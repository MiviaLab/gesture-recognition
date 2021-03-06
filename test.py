import torch
from torch.autograd import Variable
import torch.nn.functional as F
import time
import os
import sys
import json
from tqdm import tqdm

from utils import AverageMeter


def calculate_video_results(output_buffer, video_id, test_results, class_names, predictions_per_video, predictions):
    # print('Class name: {}\n'.format(class_names))
    video_outputs = torch.stack(output_buffer)
    average_scores = torch.mean(video_outputs, dim=0)
    sorted_scores, locs = torch.topk(average_scores, k=predictions_per_video)
    # print('LOCS: {}'.format(locs))
    # print('Shape: {}'.format(average_scores.size()))

    video_results = []
    for i in range(sorted_scores.size(0)):
        video_results.append({
            'label': class_names[int(locs[i])],
            'score': float(sorted_scores[i])
        })
    predictions.append(average_scores.tolist())
    test_results['results'][video_id] = video_results


def test(data_loader, model, opt, class_names):
    # print('test')

    model.eval()

    batch_time = AverageMeter()
    data_time = AverageMeter()

    end_time = time.time()
    output_buffer = []
    predictions = []
    previous_video_id = ''
    test_results = {'results': {}}
    batch_iter = tqdm(enumerate(data_loader), 'Testing', total=len(data_loader))
    for i, (inputs, targets) in batch_iter:
        data_time.update(time.time() - end_time)
        with torch.no_grad():
            inputs = Variable(inputs)
        # print('########### Input ###########\nType: {}\nTensor size: {}\n\n#############################'.format(type(inputs), inputs.size()))
        if opt.cnn_dim in [0, 3]:
            # outputs = model(inputs)
            outputs, cnns_outputs, features_outputs = model(inputs)
            # outputs, features_outputs = model(inputs)
        elif opt.cnn_dim == 2:
            outputs, cnns_outputs = model(inputs)
        else:
            print('ERROR: "cnn_dim={}" is not acceptable.'.format(opt.cnn_dim))
        # print('Type: {}\nShape: {}\nPrediction:\n{}'. format(type(outputs), outputs.shape, outputs))
        if not opt.no_softmax_in_test:
            outputs = F.softmax(outputs, dim=1)
        # print('Type: {}\nShape: {}\nPrediction:\n{}'. format(type(outputs), outputs.shape, outputs))
        for j in range(outputs.size(0)):
            if not (i == 0 and j == 0) and targets[j] != previous_video_id:
                calculate_video_results(output_buffer, previous_video_id, test_results, class_names, opt.preds_per_video, predictions)
                output_buffer = []
            output_buffer.append(outputs[j].data.cpu())
            previous_video_id = targets[j]
        '''
        if (i % 100) == 0:
            with open(
                    os.path.join(opt.result_path, '{}.json'.format(
                        opt.test_subset)), 'w') as f:
                json.dump(test_results, f)
        '''
        batch_time.update(time.time() - end_time)
        end_time = time.time()
        '''
        print('[{}/{}]\t'
              'Time {batch_time.val:.3f} ({batch_time.avg:.3f})\t'
              'Data {data_time.val:.3f} ({data_time.avg:.3f})\t'.format(
                  i + 1,
                  len(data_loader),
                  batch_time=batch_time,
                  data_time=data_time))
        '''
        # batch_iter.set_description('Testing')
    batch_iter.close()
    
    ''' Time analysis '''
    print('Time {batch_time.avg:.3f}\tData {data_time.avg:.3f}\t'.format(
                  batch_time=batch_time,
                  data_time=data_time))
    
    # Save predictions
    predictions = torch.Tensor(predictions)
    torch.save(predictions, '{}/predictions_{}.pt'.format(opt.result_path, '_'.join(modality for modality in opt.modalities)))
    
    with open(
            os.path.join(opt.result_path, '{}_{}.json'.format(opt.test_subset, '_'.join(modality for modality in opt.modalities))),
            'w') as f:
        json.dump(test_results, f)