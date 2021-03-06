import argparse


def parse_opts():
    parser = argparse.ArgumentParser()
    ############### PATH ###############
    parser.add_argument('--root_path', default='/root/data/ActivityNet', type=str, help='Root directory path of data')
    parser.add_argument('--video_path', default='video_kinetics_jpg', type=str, help='Directory path of Videos')
    parser.add_argument('--annotation_path', default='kinetics.json', type=str, help='Annotation file path')
    parser.add_argument('--result_path', default='results', type=str, help='Result directory path')
    parser.add_argument('--store_name', default='model', type=str, help='Name to store checkpoints')
    parser.add_argument('--resume_path', default='', type=str, help='Save data (.pth) of previous training')
    parser.add_argument('--pretrain_path', default='', type=str, help='Pretrained model (.pth)')
    
    ############### DEVICE ###############
    parser.add_argument('--gpu', default=None, type=str, help='GPU device')
    parser.add_argument('--no_cuda', action='store_true', help='If true, cuda is not used.')
    parser.set_defaults(no_cuda=False)
    parser.add_argument('--n_threads', default=16, type=int, help='Number of threads for multi-thread loading')
    parser.add_argument('--checkpoint', default=1, type=int, help='Trained model is saved at every this epochs.')
    parser.add_argument('--manual_seed', default=1, type=int, help='Manually set random seed')

    ############### INPUT ###############
    parser.add_argument('--dataset', default='kinetics', type=str, help='Used dataset (activitynet | kinetics | ucf101 | hmdb51 | jester | isogd)')
    parser.add_argument('--modalities', default='RGB', type=str, nargs='+', help='Modalities of input data. (RGB | D | MHI | MHI_D | OF | OF_D)')
    parser.add_argument('--n_classes', default=400, type=int, help='Number of classes (activitynet: 200, kinetics: 400, ucf101: 101, hmdb51: 51, jester: 27, isogd: 249)')
    parser.add_argument('--n_finetune_classes', default=400, type=int, help='Number of classes for fine-tuning. n_classes is set to the number when pretraining.')
    parser.add_argument('--sample_size', default=112, type=int, help='Height and width of inputs')
    parser.add_argument('--sample_duration', default=16, type=int, help='Temporal duration of inputs')
    
    ############### PRE-PROCESSING ###############
    parser.add_argument('--downsample', default=2, type=int, help='Downsampling. Selecting 1 frame out of N')
    parser.add_argument('--initial_scale', default=1.0, type=float, help='Initial scale for multiscale cropping')
    parser.add_argument('--n_scales', default=5, type=int, help='Number of scales for multiscale cropping')
    parser.add_argument('--scale_step', default=0.95, type=float, help='Scale step for multiscale cropping')
    parser.add_argument('--train_crop', default='random', type=str, help='Spatial cropping method in training. random is uniform. corner is selection from 4 corners and 1 center.  (random | corner | center)')
    parser.add_argument('--mean_dataset', default='activitynet', type=str, help='dataset for mean values of mean subtraction (activitynet | kinetics)')
    parser.add_argument('--mean_norm', action='store_true', help='If true, inputs are not normalized by mean.')
    parser.set_defaults(mean_norm=False)
    parser.add_argument('--std_norm', action='store_true', help='If true, inputs are normalized by standard deviation.')
    parser.set_defaults(std_norm=False)
    parser.add_argument('--no_hflip', action='store_true', help='If true horizontal flipping is not performed.')
    parser.set_defaults(no_hflip=False)
    parser.add_argument('--norm_value', default=1, type=int, help='If 1, range of inputs is [0-255]. If 255, range of inputs is [0-1].')
    parser.add_argument('--scale_in_test', default=1.0, type=float, help='Spatial scale in test')
    parser.add_argument('--crop_position_in_test', default='c', type=str, help='Cropping method (c | tl | tr | bl | br) in test')    
    
    ############### MODEL ###############
    parser.add_argument('--cnn_dim', default=3, type=int, help='Dimension of convolutional kernel (2 | 3')
    parser.add_argument('--model', default='resnet', type=str, help='(resnet | preresnet | wideresnet | resnext | densenet | ')
    parser.add_argument('--version', default=1.1, type=float, help='Version of the model')
    parser.add_argument('--model_depth', default=101, type=int, help='Depth of resnet (10 | 18 | 34 | 50 | 101)')
    parser.add_argument('--resnet_shortcut', default='B', type=str, help='Shortcut type of resnet (A | B)')
    parser.add_argument('--wide_resnet_k', default=2, type=int, help='Wide resnet k')
    parser.add_argument('--resnext_cardinality', default=32, type=int, help='ResNeXt cardinality')
    parser.add_argument('--groups', default=3, type=int, help='The number of groups at group convolutions at conv layers')
    parser.add_argument('--width_mult', default=1.0, type=float, help='The applied width multiplier to scale number of filters')
    parser.add_argument('--shallow_layer_num', default=2, type=int)
    parser.add_argument('--middle_layer_num', default=5, type=int)
    parser.add_argument('--high_layer_num', default=2, type=int)
    parser.add_argument('--temp_aggr', default='none', type=str, help='(MLP | LSTM | avg | max')
    parser.add_argument('--mod_aggr', default='none', type=str, help='(MLP | avg | max | none')
    parser.add_argument('--feat_fusion', action='store_true', help='If true, modalities fusion is applied to feature level')
    parser.set_defaults(feat_fusion=False)
    
    ############### TRAINING PARAMETERS ###############
    parser.add_argument('--learning_rate', default=0.04, type=float, help='Initial learning rate (divided by 10 while training by lr scheduler)')
    parser.add_argument('--lr_steps', default=None, type=int, nargs='+', metavar='LRSteps', help='epochs to decay learning rate by 10')
    parser.add_argument('--lr_linear_decay', default=None, type=float, help='Linear decay for decrement learning rate')
    parser.add_argument('--lr_patience', default=10, type=int, help='Patience of LR scheduler. See documentation of ReduceLROnPlateau.')
    parser.add_argument('--momentum', default=0.9, type=float, help='Momentum')
    parser.add_argument('--dampening', default=0.9, type=float, help='dampening of SGD')
    parser.add_argument('--weight_decay', default=1e-3, type=float, help='Weight Decay')
    parser.add_argument('--nesterov', action='store_true', help='Nesterov momentum')
    parser.set_defaults(nesterov=False)
    parser.add_argument('--optimizer', default='sgd', type=str, help='Currently only support SGD')
    parser.add_argument('--batch_size', default=128, type=int, help='Batch Size')
    parser.add_argument('--n_epochs', default=250, type=int, help='Number of total epochs to run')
    parser.add_argument('--begin_epoch', default=1, type=int, help='Training begins at this epoch. Previous trained model indicated by resume_path is loaded.')
    parser.add_argument('--n_val_samples', default=1, type=int, help='Number of validation samples for each activity')
    parser.add_argument('--no_softmax_in_test', action='store_true', help='If true, output for each clip is not normalized using softmax.')
    parser.set_defaults(no_softmax_in_test=False)
    parser.add_argument('--SSA_loss', action='store_true', help='If true, Spatiotemporal Semantic Alignment is used to fuse information of each modality during the training.')
    parser.set_defaults(feat_fusion=False)
    parser.add_argument('--ft_portion', default='complete', type=str, help='The portion of the model to apply fine tuning, either complete or last_layer')
    
    ############### OTHERS PARAMETERS ###############
    parser.add_argument('--no_train', action='store_true', help='If true, training is not performed.')
    parser.set_defaults(no_train=False)
    parser.add_argument('--no_val', action='store_true', help='If true, validation is not performed.')
    parser.set_defaults(no_val=False)
    parser.add_argument('--test', action='store_true', help='If true, test is performed.')
    parser.set_defaults(test=False)
    parser.add_argument('--test_subset', default='val', type=str, help='Used subset in test (val | test)')
    parser.add_argument('--preds_per_video', default=10, type=int, help='number of predictions returned by the system for each video')

    args = parser.parse_args()

    return args
