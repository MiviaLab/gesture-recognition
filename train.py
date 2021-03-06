import torch
from torch.autograd import Variable
import time
import os
import sys
from tqdm import tqdm
import math

from torchvision.utils import save_image

from utils import *


def train_epoch(epoch, data_loader, model, criterion, optimizer, opt, epoch_logger, batch_logger):
    # print('train at epoch {}'.format(epoch))

    model.train()

    # batch_time = AverageMeter()
    # data_time = AverageMeter()
    losses = AverageMeter()
    top1 = AverageMeter()
    top5 = AverageMeter()

    # end_time = time.time()
    batch_iter = tqdm(enumerate(data_loader), 'Train at epoch {:03d}'.format(epoch), total=len(data_loader))
    for i, (inputs, targets) in batch_iter:
        # data_time.update(time.time() - end_time)

        if opt.gpu is not None:
            targets = targets.cuda()
        # print('########### Input ###########\nType: {}\nTensor size: {}\n\n#############################'.format(type(inputs), inputs.size()))
        '''
        for frame in range(inputs.size(3)):
            image = inputs[:, 0, :, frame, :, :]
            # image = image.div(255)    # to visualize with real colors
            save_image(image, '{:02d}_{:02d}.png'.format(i, frame))
        with open('{:02d}.txt'.format(i), 'w') as f:
            for target in targets:
                f.write(str(target)+"\n")
        '''
        inputs = Variable(inputs)
        targets = Variable(targets)
        if opt.cnn_dim in [0, 3]:
            # outputs = model(inputs)
            outputs, cnns_outputs, features_outputs = model(inputs)
            # outputs, features_outputs = model(inputs)
        elif opt.cnn_dim == 2:
            outputs, cnns_outputs = model(inputs)
        else:
            print('ERROR: "cnn_dim={}" is not acceptable.'.format(opt.cnn_dim))
        
        '''
        print('*************** TRAINING ***************')
        print('Final output: {}\nCnns output: {}\nCNNs features: {}'.format(outputs.size(), cnns_outputs.size(), features_outputs.size() if (features_outputs is not None) else features_outputs))
        print('****************************************\n')
        #'''
        '''
        print('***********target shape in train: ', targets.size())
        print('********input shape in train: ', inputs.size())
        print('***********output shape in train: ', outputs.size())
        '''
        loss = criterion(outputs, targets)

        losses.update(loss.data, inputs.size(0))
        prec1, prec5 = calculate_accuracy(outputs.data, targets.data, topk=(1,5))
        top1.update(prec1, inputs.size(0))
        top5.update(prec5, inputs.size(0))

        optimizer.zero_grad()
        loss.backward()
        optimizer.step()
        
        # batch_time.update(time.time() - end_time)
        # end_time = time.time()
           
        batch_logger.log({
            'epoch': epoch,
            'batch': i + 1,
            'iter': (epoch - 1) * len(data_loader) + (i + 1),
            'loss': losses.val.item(),
            'prec1': top1.val.item(),
            'prec5': top5.val.item(),
            'lr': optimizer.param_groups[0]['lr']
        })
        
        # batch_iter.set_description(f'Train at epoch {epoch:03d}')  # update progressbar
        # batch_iter.set_description(f'Train at epoch {epoch:03d}, avgLoss: {losses.avg.item():.4f}, avgPrec@1: {top1.avg.item():.2f}, avgPrec@5: {top5.avg.item():.2f}')  # update progressbar
    batch_iter.close()
    epoch_logger.log({
        'epoch': epoch,
        'loss': losses.avg.item(),
        'prec1': top1.avg.item(),
        'prec5': top5.avg.item(),
        'lr': optimizer.param_groups[0]['lr']
    })

    #if epoch % opt.checkpoint == 0:
    #    save_file_path = os.path.join(opt.result_path,
    #                                  'save_{}.pth'.format(epoch))
    #    states = {
    #        'epoch': epoch + 1,
    #        'arch': opt.arch,
    #        'state_dict': model.state_dict(),
    #        'optimizer': optimizer.state_dict(),
    #    }
    #    torch.save(states, save_file_path)


def regularizer(losses):
    beta = 2.0
    coeffs = np.zeros((len(losses), len(losses)))
    for i in range(len(losses)):
        for j in range(len(losses)):
            # coeffs[i][j] = (beta * math.exp(losses[i] - losses[j])) - 1 if losses[i] - losses[j] > 0 else 0
            # coeffs[i][j] = math.exp(beta * (losses[i] - losses[j])) - 1 if losses[i] - losses[j] > 0 else torch.tensor([.0])
            coeffs[i][j] = 1 - math.exp(-(beta * (losses[i] - losses[j]))) if losses[i] - losses[j] > 0 else torch.tensor([.0])
    return coeffs

    
def train_epoch_custom_loss(epoch, data_loader, model, criterion, optimizers, opt, epoch_logger, batch_logger):
    # print('##########\nCriterion: {}\nOptimizers: {}\n#########\n'.format(criterion, optimizers))
    # print('train at epoch {}'.format(epoch))
    _lambda = 9e-5
    # '''
    for ii in range(len(opt.modalities)):
        model.module.cnns[ii].train()
    '''
    model.train()
    
    
    for name, param in model.module.cnns[0].named_parameters():
        print(name)
    '''
    # batch_time = AverageMeter()
    # data_time = AverageMeter()
    losses = AverageMeter()
    top1 = AverageMeter()
    top5 = AverageMeter()

    # end_time = time.time()
    batch_iter = tqdm(enumerate(data_loader), 'Train at epoch {:03d}'.format(epoch), total=len(data_loader))
    for i, (inputs, targets) in batch_iter:
        # data_time.update(time.time() - end_time)

        if not opt.no_cuda:
            targets = targets.cuda()
        # print('########### Input ###########\nType: {}\nTensor size: {}\n\n#############################'.format(type(inputs), inputs.size()))
        inputs = Variable(inputs)
        targets = Variable(targets)
        outputs, cnns_outputs, features_outputs = model(inputs)
        # print('Final output: {}\nCnns output: {}\nCNNs features: {}'.format(outputs.size(), cnns_outputs.size(), features_outputs.size()))
        mods_losses = list()
        corrs = list()
        final_loss = 0.
        for ii in range(len(opt.modalities)):
            optimizers[ii].zero_grad()
            # print(output)
            # print('### Feature map size: ', feat_map.size())
            feat_map_T = torch.transpose(features_outputs[ii], 1, 2)
            sq_feat_map = feat_map_T.squeeze()
            # avg_feat_map = sq_feat_map
            corr = torch.mul(features_outputs[ii], feat_map_T)
            corrs.append(corr)
            loss = criterion(cnns_outputs[ii], targets)   # index of the max log-probability
            mods_losses.append(loss)
        focal_reg_params = regularizer(mods_losses)
        # print('##### focal_reg_params #####\n{}###################', focal_reg_params)
        ssa_loss = 0.
        for ii in range(len(opt.modalities)):
            # print('modality: {}'.format(opt.modalities[ii]))
            for jj in range(len(opt.modalities)):
                if jj != ii:
                    corr_diff = torch.sqrt(torch.sum(torch.sub(corrs[ii], corrs[jj]) ** 2))
                    ssa_loss += focal_reg_params[ii][jj] * corr_diff
            reg_loss = loss + (_lambda * ssa_loss)
            final_loss += reg_loss
            # print('##### Output #####\n{} + {} = {}\n###################'.format(loss, _lambda * ssa_loss, reg_loss))
            
            # optimizers[ii].zero_grad()
            if ii < (len(opt.modalities) - 1): 
                reg_loss.backward(retain_graph=True)
            else:
                reg_loss.backward()
            '''
            for name, param in model.module.cnns[ii].named_parameters():
                print(name, torch.isfinite(param.grad).all())
            '''  
        for ii in range(len(opt.modalities)):
            optimizers[ii].step()
        
        losses.update(final_loss, inputs.size(0))
        #outputs = model(inputs)
        prec1, prec5 = calculate_accuracy(outputs.data, targets.data, topk=(1,5))
        top1.update(prec1, inputs.size(0))
        top5.update(prec5, inputs.size(0))
        
        # batch_time.update(time.time() - end_time)
        # end_time = time.time()
           
        batch_logger.log({
            'epoch': epoch,
            'batch': i + 1,
            'iter': (epoch - 1) * len(data_loader) + (i + 1),
            'loss': losses.val.item(),
            'prec1': top1.val.item(),
            'prec5': top5.val.item(),
            'lr': optimizers[0].param_groups[0]['lr']
        })

        # batch_iter.set_description(f'Train at epoch {epoch:03d}')  # update progressbar
        # batch_iter.set_description(f'Train at epoch {epoch:03d}, avgLoss: {losses.avg.item():.4f}, avgPrec@1: {top1.avg.item():.2f}, avgPrec@5: {top5.avg.item():.2f}')  # update progressbar
    batch_iter.close()
    epoch_logger.log({
        'epoch': epoch,
        'loss': losses.avg.item(),
        'prec1': top1.avg.item(),
        'prec5': top5.avg.item(),
        'lr': optimizers[0].param_groups[0]['lr']
    })