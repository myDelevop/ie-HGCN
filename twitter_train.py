import numpy as np
import torch
import torch.nn.functional as F
import torch.optim as optim
from sklearn.metrics import f1_score

import warnings
import sklearn.exceptions
warnings.filterwarnings("ignore", category=sklearn.exceptions.UndefinedMetricWarning)

import time

from util_twitter import *
from model import HGCN

def train(epoch):

    model.train()
    optimizer.zero_grad()
    logits, _ = model(ft_dict, adj_dict)

    u_logits = F.log_softmax(logits['u'], dim=1)
    idx_train_u = label['u'][1]
    x_train_u = u_logits[idx_train_u]
    y_train_u = label['u'][0][idx_train_u]
    loss_train = F.nll_loss(x_train_u, y_train_u)
    f1_micro_train_u = f1_score(y_train_u.data.cpu(), x_train_u.data.cpu().argmax(1), average='micro')
    f1_macro_train_u = f1_score(y_train_u.data.cpu(), x_train_u.data.cpu().argmax(1), average='macro')

    loss_train.backward()
    optimizer.step()


    if epoch % 1 == 0:
        print(
            'epoch: {:3d}'.format(epoch),
            'train loss: {:.4f}'.format(loss_train.item()),
            'train micro f1 u {:.4f}'.format(f1_micro_train_u.item()),
            'train macro f1 u: {:.4f}'.format(f1_macro_train_u.item()),
        )

def test():
    model.eval()
    logits, embd = model(ft_dict, adj_dict)

    u_logits = F.log_softmax(logits['u'], dim=1)
    idx_test_u = label['u'][2]
    x_test_u = u_logits[idx_test_u]
    y_test_u = label['u'][0][idx_test_u]
    f1_micro_test_u = f1_score(y_test_u.data.cpu(), x_test_u.data.cpu().argmax(1), average='micro')
    f1_macro_test_u = f1_score(y_test_u.data.cpu(), x_test_u.data.cpu().argmax(1), average='macro')


    print(
        '\n'+
        'test micro f1 u: {:.4f}'.format(f1_micro_test_u.item()),
        'test macro f1 u: {:.4f}'.format(f1_macro_test_u.item()),
    )

    return (f1_micro_test_u, f1_macro_test_u)

if __name__ == '__main__':

    cuda = True # Enables CUDA training.
    lr = 0.01 # Initial learning rate.c
    weight_decay = 5e-4 # Weight decay (L2 loss on parameters).
    type_att_size = 64 # type attention parameter dimension
    type_fusion = 'att' # mean

    run_num = 1
    for run in range(run_num):
        t_start = time.time()
        seed = run

        np.random.seed(seed)
        torch.manual_seed(seed)
        if cuda and torch.cuda.is_available():
            torch.cuda.manual_seed(seed)

        print('\nHGCN run: ', run)
        print('seed: ', seed)
        print('type fusion: ', type_fusion)
        print('type att size: ', type_att_size)

        hid_layer_dim = [64,32,16,8]  # imdb3228
        epochs = 250
        label, ft_dict, adj_dict = load_twitter()
        output_layer_shape = dict.fromkeys(ft_dict.keys(), 2)

        layer_shape = []
        input_layer_shape = dict([(k, ft_dict[k].shape[1]) for k in ft_dict.keys()])
        layer_shape.append(input_layer_shape)
        hidden_layer_shape = [dict.fromkeys(ft_dict.keys(), l_hid) for l_hid in hid_layer_dim]
        layer_shape.extend(hidden_layer_shape)
        layer_shape.append(output_layer_shape)

        # Model and optimizer
        net_schema = dict([(k, list(adj_dict[k].keys())) for k in adj_dict.keys()])
        model = HGCN(
            net_schema=net_schema,
            layer_shape=layer_shape,
            label_keys=list(label.keys()),
            type_fusion=type_fusion,
            type_att_size=type_att_size,
        )
        optimizer = optim.Adam(model.parameters(), lr=lr, weight_decay=weight_decay)

        if cuda and torch.cuda.is_available():
            model.cuda()

            for k in ft_dict:
                ft_dict[k] = ft_dict[k].cuda()
            for k in adj_dict:
                for kk in adj_dict[k]:
                    adj_dict[k][kk] = adj_dict[k][kk].cuda()
            for k in label:
                for i in range(len(label[k])):
                    label[k][i] = label[k][i].cuda()

        for epoch in range(epochs):
            train(epoch)

        (micro_f1, macro_f1) = test()

        t_end = time.time()
        print('Total time: ', t_end - t_start)
