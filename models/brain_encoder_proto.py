import sys
import numpy as np
import torch
import torch.nn as nn
from time import time
from utils.layout import ch_locations_2d
import torch.nn.functional as F
from constants import device
from termcolor import cprint


class SpatialAttentionVer1(nn.Module):
    """This is easier to understand but very slow. I reimplemented to SpatialAttentionVer2"""

    def __init__(self, args, z_re=None, z_im=None):
        super(SpatialAttentionVer1, self).__init__()

        self.D1 = args.D1
        self.K = args.K

        if z_re is None or z_im is None:
            self.z_re = nn.Parameter(torch.Tensor(self.D1, self.K, self.K))
            self.z_im = nn.Parameter(torch.Tensor(self.D1, self.K, self.K))
            nn.init.kaiming_uniform_(self.z_re, a=np.sqrt(5))
            nn.init.kaiming_uniform_(self.z_im, a=np.sqrt(5))
        else:
            self.z_re = z_re
            self.z_im = z_im

        self.ch_locations_2d = ch_locations_2d(args.dataset).cuda()

    def fourier_space(self, j, x: torch.Tensor, y: torch.Tensor):  # x: ( 60, ) y: ( 60, )
        a_j = 0
        for k in range(self.K):
            for l in range(self.K):
                a_j += self.z_re[j, k, l] * torch.cos(2 * torch.pi * (k * x + l * y))
                a_j += self.z_im[j, k, l] * torch.sin(2 * torch.pi * (k * x + l * y))

        return a_j  # ( 60, )

    def forward(self, X):  # ( B, C, T ) (=( 128, 60, 256 ))
        spat_attn = []
        loc = self.ch_locations_2d  # ( 60, 2 )
        for j in range(self.D1):
            a_j = self.fourier_space(j, loc[:, 0], loc[:, 1])  # ( 60, )

            # sa.append(torch.exp(a_j) @ X / torch.exp(a_j).sum()) # ( 128, 256 )
            spat_attn.append(torch.einsum('c,bct->bt', torch.exp(a_j), X) / torch.exp(a_j).sum())  # ( 128, 256 )

        spat_attn = torch.stack(spat_attn)  # ( 270, 128, 256 )

        return spat_attn.permute(1, 0, 2)  # ( 128, 270, 256 )


class SpatialAttentionVer2(nn.Module):
    """Faster version of SpatialAttentionVer1"""

    def __init__(self, args):
        super(SpatialAttentionVer2, self).__init__()

        self.D1 = args.D1
        self.K = args.K

        self.z_re = nn.Parameter(torch.Tensor(self.D1, self.K, self.K))
        self.z_im = nn.Parameter(torch.Tensor(self.D1, self.K, self.K))
        nn.init.kaiming_uniform_(self.z_re, a=np.sqrt(5))
        nn.init.kaiming_uniform_(self.z_im, a=np.sqrt(5))

        self.K_arange = torch.arange(self.K).to(device)

        self.ch_locations_2d = ch_locations_2d(args.dataset).cuda()

    def fourier_space(self, x: torch.Tensor, y: torch.Tensor):  # x: ( 60, ) y: ( 60, )

        rad1 = torch.einsum('k,c->kc', self.K_arange, x)
        rad2 = torch.einsum('l,c->lc', self.K_arange, y)
        # rad = torch.einsum('kc,lc->kcl', rad1, rad2)

        # ( 32, 1, 60 ) + ( 1, 32, 60 ) -> ( 32, 32, 60 )
        rad = rad1.unsqueeze(1) + rad2.unsqueeze(0)

        real = torch.einsum('dkl,klc->dc', self.z_re, torch.cos(2 * torch.pi * rad))  # ( 270, 60 )
        imag = torch.einsum('dkl,klc->dc', self.z_im, torch.sin(2 * torch.pi * rad))

        return real + imag  # ( 270, 60 )

    def fourier_space_orig(self, x: torch.Tensor, y: torch.Tensor):  # x: ( 60, ) y: ( 60, )
        """Slower version of fourier_space"""

        a = torch.zeros(self.D1, x.shape[0], device=device)  # ( 270, 60 )
        for k in range(self.K):
            for l in range(self.K):
                # This einsum is same as torch.stack([_d * c for _d in d])
                a += torch.einsum('d,c->dc', self.z_re[:, k, l],
                                  torch.cos(2 * torch.pi * (k * x + l * y)))  # ( 270, 60 )
                a += torch.einsum('d,c->dc', self.z_im[:, k, l], torch.sin(2 * torch.pi * (k * x + l * y)))

        return a  # ( 270, 60 )

    def forward(self, X):  # ( 128, 60, 256 )
        loc = self.ch_locations_2d  # ( 60, 2 )

        a = self.fourier_space(loc[:, 0], loc[:, 1])  # ( 270, 60 )
        # _a = self.fourier_space_orig(loc[:,0], loc[:,1]) # ( 270, 60 )
        # print(torch.equal(_a, a))

        # ( 270, 60 ) @ ( 128, 60, 256 ) -> ( 128, 256, 270 )
        spat_attn = torch.einsum('dc,bct->btd', torch.exp(a), X) / torch.exp(a).sum(dim=1)

        return spat_attn.permute(0, 2, 1)  # ( 128, 270, 256 )


class SpatialDropoutX(nn.Module):
    # NOTE: each item in a batch gets the same channels masked (<- "same"?)
    # NOTE: with for-loop

    def __init__(self, args):
        super(SpatialDropoutX, self).__init__()
        self.d_drop = args.d_drop
        self.bsz = args.batch_size

        loc = ch_locations_2d(args.dataset)
        self.loc = [loc[i, :].flatten() for i in range(loc.shape[0])]

    def make_mask(self):
        # TODO: could just pre-compute all the possilbe drop locations
        mask = torch.ones(size=(self.bsz, len(self.loc)))
        for b in range(self.bsz):
            drop_id = np.random.choice(len(self.loc))
            drop_center = self.loc[drop_id]
            for i, coord in enumerate(self.loc):
                if (coord - drop_center).norm() < self.d_drop:
                    mask[b, i] *= 0.0
        return mask.to(device)

    def forward(self, X):
        print(self.training)
        if self.training:
            mask = self.make_mask()  # mask: B by num_chans. Each item in batch gets a different mask
            return torch.einsum('bc,bct->bct', mask, X)
        else:
            return X