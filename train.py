from data import get_datasets
from trainer import TravelGAN
from torch.utils.data.dataloader import DataLoader
# from utils import get_device, load_json, get_writer
from utils import get_device, load_json, data_load
import argparse
from statistics import mean
import torch
import os
import matplotlib.pyplot as plt
import random
import torchvision.transforms as transforms


parser = argparse.ArgumentParser()
parser.add_argument("--log", type=str, default='./log_gan_real_to_cartoon/', help="name of log folder")
parser.add_argument("-p", "--hparams", type=str, default='cifar', help="hparams config file")
parser.add_argument('--project_name', required=False, default='GAN_real_to_cartoon',  help='project name')
parser.add_argument('--input_size', type=int, default=64, help='input size')

opts = parser.parse_args()

print(opts)
device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')

if not os.path.isdir(os.path.join(opts.project_name + '_results', 'Transfer')):
    os.makedirs(os.path.join(opts.project_name + '_results', 'Transfer'))

if not os.path.isdir(opts.log):
    os.makedirs(os.path.join(opts.log))

# Generate seed
opts.manualSeed = random.randint(1, 10000)
random.seed(opts.manualSeed)
torch. manual_seed(opts.manualSeed)
print('Random Seed: ', opts.manualSeed)

# Transform dataset
src_transform = transforms.Compose([
        transforms.Resize((opts.input_size, opts.input_size)),
        transforms.ToTensor(),
        transforms.Normalize(mean=(0.5, 0.5, 0.5), std=(0.5, 0.5, 0.5))
])

tgt_transform = transforms.Compose([
        transforms.Resize((opts.input_size, opts.input_size)),
        transforms.ToTensor(),
        transforms.Normalize(mean=(0.5, 0.5, 0.5), std=(0.5, 0.5, 0.5))
])

print('Loading data..')
hparams = load_json('./configs', opts.hparams)

loading = hparams['loading']
train_loader_src = data_load(os.path.join('./../../../data/', 'faces_bg_removed/'), 'train', src_transform, batch_size=loading['batch_size'], shuffle=loading['shuffle'], drop_last=True)
train_loader_tgt = data_load(os.path.join('./../../../data/', 'bitmoji/'), 'all_gender', tgt_transform, batch_size=loading['batch_size'], shuffle=loading['shuffle'], drop_last=True)
test_loader_src = data_load(os.path.join('./../../../data/', 'faces_bg_removed/'), 'test', src_transform, batch_size=loading['batch_size'], shuffle=loading['shuffle'], drop_last=True)

model = TravelGAN(hparams['model'], device=device)
if  hparams['saved_model'] :
    print('saved model : ', hparams['saved_model'])
    model.resume(hparams['saved_model'])

print('Start training..')
for epoch in range(hparams['n_epochs']):
    # Run one epoch
    gen_losses, dis_losses = [], []
    for (x_a, _ ), (x_b,_) in zip(train_loader_src, train_loader_tgt):
        x_a = x_a.to(device, non_blocking=True)
        x_b = x_b.to(device, non_blocking=True)

        # Calculate losses and update weights
        dis_loss = model.dis_update(x_a, x_b)

        # Calculate losses and update weights
        x_ab, x_ba, gen_loss = model.gen_update(x_a, x_b)
        gen_losses.append(gen_loss)
        dis_losses.append(dis_loss)

    # Logging losses
    gen_loss, dis_loss = mean(gen_losses), mean(dis_losses)
   
    if epoch % 2 == 1 or epoch == hparams['n_epochs'] - 1:
        n = 0
        for (x_a, _ ), (x_b,_) in zip(train_loader_src, train_loader_tgt):
       
            x_a = x_a.to(device, non_blocking=True)
            x_b = x_b.to(device, non_blocking=True)

            x_ab, x_ba, gen_loss = model.gen_update(x_a, x_b)
            x_ab = x_ab.detach()
            x_ba = x_ba.detach()
            result_1 = torch.cat((x_a[0], x_ab[0]), 2)
            result_2 = torch.cat((x_b[0], x_ba[0]), 2)
            # path = os.path.join(opts.project_name + '_results', 'Transfer', str(epoch+1) + '_epoch_' + opts.project_name + '_train_' + str(n + 1) + '.png')
            path_1 = os.path.join(opts.project_name + '_results', 'Transfer', str(epoch+1) + '_epoch_' + opts.project_name + '_train_AtoB' + '.png')
            path_2 = os.path.join(opts.project_name + '_results', 'Transfer', str(epoch+1) + '_epoch_' + opts.project_name + '_train_BtoA' + '.png')
            plt.imsave(path_1, (result_1.cpu().numpy().transpose(1, 2, 0) + 1) / 2)
            plt.imsave(path_2, (result_2.cpu().numpy().transpose(1, 2, 0) + 1) / 2)
           
            n += 1
            break

        print('Epoch: %d ,Gen loss: %.2f' % (epoch, gen_loss))

    # Saving model every n_save_steps epochs
    if (epoch + 1) % hparams['n_save_steps'] == 0:
        model.save(opts.log, epoch)
