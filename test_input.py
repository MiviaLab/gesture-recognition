''' Bash command
python3 test_input.py --root_path ./ --video_path ../../../../mnt/sdc1/sbini/isogd --annotation_path annotation_ChaLearn_IsoGD/chalearn_reduced.json --result_path results/chalearn_isogd --dataset isogd --n_classes 249 --n_finetune_classes 249 --ft_portion complete --cnn_dim 3 --model resnext --model_depth 101 --groups 3 --train_crop random --scale_step 0.95 --n_epochs 60 --lr_steps 30 45 --learning_rate 0.01 --sample_duration 16 --downsample 2 --batch_size 32 --n_threads 8 --checkpoint 1 --n_val_samples 1 --no_hflip --modalities RGB --aggr_type none --gpu 3
python3 test_input.py --root_path ./ --video_path ../../../../mnt/sdc1/sbini/nvgesture --annotation_path annotation_NVGesture/test_dataloader.json --result_path results/nvgesture --dataset nvgesture --n_classes 25 --n_finetune_classes 25 --ft_portion complete --cnn_dim 3 --model resnext --model_depth 101 --groups 3 --train_crop random --scale_step 0.95 --n_epochs 60 --lr_steps 30 45 --learning_rate 0.01 --sample_duration 16 --downsample 2 --batch_size 8 --n_threads 8 --checkpoint 1 --n_val_samples 1 --no_hflip --modalities RGB --aggr_type none --gpu 3
'''
import numpy as np
import torch
from torch import nn
from torch import optim
from torch.optim import lr_scheduler
import os
import sys
import json
from opts import parse_opts
from mean import get_mean, get_std
from spatial_transforms import *
from temporal_transforms import *
from target_transforms import ClassLabel, VideoID
from target_transforms import Compose as TargetCompose
from dataset import get_training_set, get_validation_set, get_test_set
from datasets.isogd import IsoGD, pil_loader
from utils import *
from torchvision.utils import save_image
from skimage import io, color
import PIL


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

if opt.no_mean_norm and not opt.std_norm or opt.modalities != 'RGB':
    norm_method = Normalize([0, 0, 0], [1, 1, 1])
elif not opt.std_norm:
    norm_method = Normalize(opt.mean, [1, 1, 1])
else:
    norm_method = Normalize(opt.mean, opt.std)

subset= ''

if not opt.no_train:
    subset = 'train'
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
        #RandomRotate(),
        #RandomResize(),
        crop_method,
        #MultiplyValues(),
        #Dropout(),
        #SaltImage(),
        #Gaussian_blur(),
        #SpatialElasticDisplacement(),
        ToTensor(opt.norm_value), norm_method
    ])
    temporal_transform = TemporalRandomCrop(opt.sample_duration, opt.downsample)
    target_transform = ClassLabel()
    training_data = get_training_set(opt, spatial_transform, temporal_transform, target_transform)
    train_loader = torch.utils.data.DataLoader(
        training_data,
        batch_size=opt.batch_size,
        shuffle=True,
        num_workers=opt.n_threads,
        pin_memory=True)
    for i, (inputs, targets) in enumerate(train_loader):
        # inputs = Variable(inputs)
        # targets = Variable(targets)
        print('*********** Inputs ***********\n{}\n*****************************'. format(inputs.size()))
        n_frames = inputs.shape[2] if opt.cnn_dim == 2 else inputs.shape[3]
        for frame in range(n_frames):
            image = inputs[:, 0, frame, :, :, :] if opt.cnn_dim == 2 else inputs[:, 0, :, frame, :, :]
            image = image.mul(opt.norm_value)
            image = image.div(255)
            # print('*********** Image ***********\n{}\n*****************************'. format(image.size()))
            path = '{}/image{:05d}_{}.jpg'.format(opt.result_path, frame, subset)
            # print('Path: ' + path )
            save_image(image, path)
if not opt.no_val:
    subset = 'validation'
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
        batch_size=opt.batch_size,
        shuffle=False,
        num_workers=opt.n_threads,
        pin_memory=True)
    for i, (inputs, targets) in enumerate(val_loader):
        # inputs = Variable(inputs)
        # targets = Variable(targets)
        print('*********** Inputs ***********\n{}\n*****************************'. format(inputs.size()))
        for frame in range(inputs.shape[2]):
            image = inputs[:, 0, :, frame, :, :]
            image = image.mul(opt.norm_value)
            image = image.div(255)
            # print('*********** Image ***********\n{}\n*****************************'. format(image.size()))
            path = '{}/image{:05d}_{}.jpg'.format(opt.result_path, frame, subset)
            print('Path: ' + path )
            save_image(image, path)
if opt.test:
    subset = 'test'
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
    # target_transform = ClassLabel()

    test_data = get_test_set(opt, spatial_transform, temporal_transform,
                             target_transform)
    test_loader = torch.utils.data.DataLoader(
        test_data,
        batch_size=1,
        shuffle=False,
        num_workers=opt.n_threads,
        pin_memory=True)
    
    for i, (inputs, targets) in enumerate(test_loader):
        # inputs = Variable(inputs)
        # targets = Variable(targets)
        # print('*********** Inputs ***********\n{}\n*****************************'. format(inputs.shape))
        for frame in range(inputs.shape[2]):
            image = inputs[:, 0, :, frame, :, :]
            image = image.mul(opt.norm_value)
            image = image.div(255)
            # print('*********** Image ***********\n{}\n*****************************'. format(image))
            path = '{}/image{:05d}_{}.jpg'.format(opt.result_path, frame, subset)
            print('Path: ' + path )
            save_image(image, path)


