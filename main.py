import os
import sys
import json
import numpy as np
import torch
from torch import nn
from torch import optim
from torch.optim import lr_scheduler
from pytorch_model_summary import summary
import copy

from opts import parse_opts
from model import generate_model, generate_model_2d, generate_model_3d
from mean import get_mean, get_std
from spatial_transforms import *
from temporal_transforms import *
from target_transforms import ClassLabel, VideoID
from target_transforms import Compose as TargetCompose
from dataset import get_training_set, get_validation_set, get_test_set
from utils import *
from train import train_epoch, train_epoch_custom_loss
from validation import val_epoch
import test
from torchinfo import summary
# from torchsummary import summary


if __name__ == '__main__':
    opt = parse_opts()
    os.environ['CUDA_VISIBLE_DEVICES']=opt.gpu
    if opt.root_path != '':
        opt.video_path = os.path.join(opt.root_path, opt.video_path)
        opt.annotation_path = os.path.join(opt.root_path, opt.annotation_path)
        opt.result_path = os.path.join(opt.root_path, opt.result_path)
        if not os.path.exists(opt.result_path):
            os.makedirs(opt.result_path)
        if opt.resume_path:
            opt.resume_path = os.path.join(opt.root_path, opt.resume_path)
        if opt.pretrain_path:
            opt.pretrain_path = os.path.join(opt.root_path, opt.pretrain_path)
    opt.scales = [opt.initial_scale]
    for i in range(1, opt.n_scales):
        opt.scales.append(opt.scales[-1] * opt.scale_step)
    opt.arch = '{}'.format(opt.model)
    opt.mean = get_mean(opt.norm_value, dataset=opt.mean_dataset)
    opt.std = get_std(opt.norm_value)
    opt.store_name = '_'.join([opt.dataset, opt.model, '_'.join([modality for modality in opt.modalities]), opt.aggr_type])
    print(opt)
    with open(os.path.join(opt.result_path, 'opts_{}_{}_{}.json'.format(opt.dataset, opt.model, '_'.join([modality for modality in opt.modalities]), opt.aggr_type)), 'w') as opt_file:
        json.dump(vars(opt), opt_file)

    torch.manual_seed(opt.manual_seed)
    
    input_shape = (opt.batch_size, 3, opt.sample_duration, opt.sample_size, opt.sample_size)
    if opt.cnn_dim == 3:
        # model, parameters = generate_model(opt)
        model, parameters = generate_model_3d(opt)
    else:
        model, parameters = generate_model_2d(opt)
        input_shape = (opt.batch_size, opt.sample_duration, 3, opt.sample_size, opt.sample_size)
    '''
    print('######### Parameters: #########')
    pytorch_total_params = sum(p.numel() for p in model.parameters() if
                               p.requires_grad)
    no_train_params = sum(p.numel() for p in model.parameters() if not
                               p.requires_grad)
    print("Total number of trainable parameters: ", pytorch_total_params)
    print("Total number of non-trainable parameters: ", no_train_params)
    
    print('###############################')
    #'''
    # print('Input model shape: ', input_shape)
    # model_sum = summary(model.module, input_shape)
    '''
    for name, param in model.state_dict().items():
        print(name)
    '''
    criterion = nn.CrossEntropyLoss()
    if opt.gpu not None:
        criterion = criterion.cuda()

    # if opt.no_mean_norm and not opt.std_norm or opt.modality != 'RGB':
    if opt.no_mean_norm and not opt.std_norm:
        norm_method = Normalize([0, 0, 0], [1, 1, 1])
    elif not opt.std_norm:
        norm_method = Normalize(opt.mean, [1, 1, 1])
    else:
        norm_method = Normalize(opt.mean, opt.std)

    if not opt.no_train:
        assert opt.train_crop in ['random', 'corner', 'center', 'none']
        if opt.train_crop == 'random':
            crop_method = MultiScaleRandomCrop(opt.scales, opt.sample_size)
        elif opt.train_crop == 'corner':
            crop_method = MultiScaleCornerCrop(opt.scales, opt.sample_size)
        elif opt.train_crop == 'center':
            crop_method = MultiScaleCornerCrop(
                opt.scales, opt.sample_size, crop_positions=['c'])
        elif opt.train_crop == 'none':
            crop_method = Scale(opt.sample_size)
            # crop_method = Scale_original(opt.sample_size)
        spatial_transform = Compose([
            #RandomHorizontalFlip(),
            RandomRotate(),
            RandomResize(),
            crop_method,
            MultiplyValues(),
            #Dropout(),
            #SaltImage(),
            #Gaussian_blur(),
            #SpatialElasticDisplacement(),
            ToTensor(opt.norm_value), norm_method
        ])
        temporal_transform = TemporalRandomCrop(opt.sample_duration, opt.downsample)
        target_transform = ClassLabel()
        training_data = get_training_set(opt, spatial_transform,
                                         temporal_transform, target_transform)
        train_loader = torch.utils.data.DataLoader(
            training_data,
            batch_size=opt.batch_size,
            shuffle=True,
            num_workers=opt.n_threads,
            pin_memory=True)
        train_logger = Logger(
            os.path.join(opt.result_path, 'train{}.log'.format(''.join(['_'+modality for modality in opt.modalities]))),
            ['epoch', 'loss', 'prec1', 'prec5', 'lr'])
        train_batch_logger = Logger(
            os.path.join(opt.result_path, 'train_batch{}.log'.format(''.join(['_'+modality for modality in opt.modalities]))),
            ['epoch', 'batch', 'iter', 'loss', 'prec1', 'prec5', 'lr'])

        if opt.nesterov:
            dampening = 0
        else:
            dampening = opt.dampening
        
        optimizers = list()
        schedulers = list()
        optimizer = None
        
        for i in range(len(opt.modalities)):
            if opt.SSA_loss:
                params = model.module.cnns[i].parameters()
            else:
                params = model.parameters()
            optimizer = optim.SGD(
                params=params,
                lr=opt.learning_rate,
                momentum=opt.momentum,
                dampening=dampening,
                weight_decay=opt.weight_decay,
                nesterov=opt.nesterov)
            optimizers.append(optimizer)
            
            if opt.lr_linear_decay:
                #the error can be done here
                lr_step = (opt.learning_rate - opt.lr_linear_decay) / opt.n_epochs
                lr_func = lambda epoch: (opt.n_epochs - epoch) / opt.n_epochs
                scheduler = lr_scheduler.MultiplicativeLR(optimizer, lr_lambda=lr_func)   # linear decreasing of the learning rate
            elif opt.lr_steps is None:
                scheduler = lr_scheduler.ReduceLROnPlateau(optimizer, 'max', patience=opt.lr_patience)
            else:
                scheduler = lr_scheduler.MultiStepLR(optimizer, milestones=opt.lr_steps, gamma=0.1)
            schedulers.append(scheduler)
        
    if not opt.no_val:
        spatial_transform = Compose([
            # Scale_original(opt.sample_size),        # insert by beis
            Scale(opt.sample_size),         # comment by beis
            # CenterCrop(opt.sample_size),  # comment by beis
            ToTensor(opt.norm_value), norm_method
        ])
        #temporal_transform = LoopPadding(opt.sample_duration)
        temporal_transform = TemporalCenterCrop(opt.sample_duration, opt.downsample)
        target_transform = ClassLabel()
        validation_data = get_validation_set(
            opt, spatial_transform, temporal_transform, target_transform)
        val_loader = torch.utils.data.DataLoader(
            validation_data,
            # batch_size=16,
            batch_size=opt.batch_size,
            shuffle=False,
            num_workers=opt.n_threads,
            pin_memory=True)
        val_log_info = ['epoch', 'loss', 'prec1', 'prec5']
        for modality in opt.modalities:
            val_log_info.append(modality+'_prec1')
        val_logger = Logger(os.path.join(opt.result_path, 'val{}.log'.format(''.join(['_'+modality for modality in opt.modalities]))), val_log_info)

    best_prec1 = 0
    mods_best_prec1 = list([0. for modality in opt.modalities])
    if opt.resume_path:
        print('loading checkpoint {}'.format(opt.resume_path))
        checkpoint = torch.load(opt.resume_path)
        assert opt.arch == checkpoint['arch']
        best_prec1 = checkpoint['best_prec1']
        opt.begin_epoch = checkpoint['epoch']
        print(checkpoint)
        model.load_state_dict(checkpoint['state_dict'])


    # print('run')
    for i in range(opt.begin_epoch, opt.n_epochs + 1):

        if not opt.no_train:
            # adjust_learning_rate(optimizer, i, opt)
            if opt.SSA_loss:
                train_epoch_custom_loss(i, train_loader, model, criterion, optimizers, opt, train_logger, train_batch_logger)
            else:
                train_epoch(i, train_loader, model, criterion, optimizers[0], opt, train_logger, train_batch_logger)
            state = {
                'epoch': i,
                'arch': opt.arch,
                'state_dict': model.state_dict(),
                'optimizer': optimizer.state_dict(),
                'best_prec1': best_prec1
                }
            save_checkpoint(state, False, opt)
            
        if not opt.no_val:
            validation_loss, prec1, mods_prec1 = val_epoch(i, val_loader, model, criterion, opt, val_logger)
            if opt.SSA_loss:
                for i in range(len(opt.modalities)):
                    if opt.lr_steps is None and opt.lr_linear_decay is None:
                        schedulers[i].step(prec1)   # check if the prec1 is increased
                    else:
                        schedulers[i].step()
            else:
                if opt.lr_steps is None and opt.lr_linear_decay is None:
                    schedulers[0].step(prec1)   # check if the prec1 is increased
                else:
                    schedulers[0].step()
            is_best = prec1 > best_prec1
            best_prec1 = max(prec1, best_prec1)
            state = {
                'epoch': i,
                'arch': opt.arch,
                'state_dict': model.state_dict(),
                'optimizer': optimizer.state_dict(),
                'best_prec1': best_prec1
                }
            save_checkpoint(state, is_best, opt)
            # Save the singol network
            if opt.SSA_loss:
                for modality in range(len(opt.modalities)):
                    if mods_best_prec1[modality] > mods_prec1[modality]:
                        mods_best_prec1[modality] = mods_prec1[modality]
                        for ii in range(len(opt.modalities)):
                            torch.save(model.module.cnns[ii].state_dict(), '{}/{}_{}_{}_SSA_loss.pth'.format(opt.result_path, opt.dataset, opt.model, opt.modalities[ii]))

    if opt.test:
        spatial_transform = Compose([
            # Scale_original(opt.sample_size),
            # Scale(int(opt.sample_size / opt.scale_in_test)),
            Scale(opt.sample_size),
            # CornerCrop(opt.sample_size, opt.crop_position_in_test),
            # CenterCrop(opt.sample_size),
            ToTensor(opt.norm_value), norm_method
        ])
        # temporal_transform = LoopPadding(opt.sample_duration, opt.downsample)
        # temporal_transform = TemporalRandomCrop(opt.sample_duration, opt.downsample)
        temporal_transform = TemporalCenterCrop(opt.sample_duration, opt.downsample)
        target_transform = VideoID()

        test_data = get_test_set(opt, spatial_transform, temporal_transform,
                                 target_transform)
        test_loader = torch.utils.data.DataLoader(
            test_data,
            # batch_size=16,
            batch_size=opt.batch_size,
            shuffle=False,
            num_workers=opt.n_threads,
            pin_memory=True)
        test.test(test_loader, model, opt, test_data.class_names)