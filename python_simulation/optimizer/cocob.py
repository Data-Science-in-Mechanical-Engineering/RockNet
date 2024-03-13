from torch.optim.optimizer import Optimizer
import torch
device = "cuda" if torch.cuda.is_available() else "cpu"


class COCOB_Backprop_old(Optimizer):
    """Implementation of the COCOB algorithm.
    Arguments:
        params (iterable): iterable of parameters to optimize or dicts defining
            parameter groups
        weight_decay (float, optional): weight decay (L2 penalty) (default: 0)

    Usage:
    1. Put cocob_bp.py in YOUR_PYTHON_PATH/site-packages/torch/optim.
    2. Open YOUR_PYTHON_PATH/site-packages/torch/optim/__init__.py add the following code:
    ```
    from .cocob_bp import COCOB_Backprop
    del cocob_bp
    ```
    3. Save __init__.py and restart your python.
    Use COCOB_Backprop as

    optimizer = optim.COCOB_Backprop(net.parameters())
    ...
    optimizer.step()

    Implemented by Huidong Liu
    Email: huidliu@cs.stonybrook.edu or h.d.liew@gmail.com

    References
    [1] Francesco Orabona and Tatiana Tommasi, Training Deep Networks without Learning Rates
    Through Coin Betting, NIPS 2017.

    """

    def __init__(self, params, weight_decay=0, alpha=100):
        defaults = dict(weight_decay=weight_decay)
        super(COCOB_Backprop, self).__init__(params, defaults)
        # COCOB initializaiton
        self.W1 = []
        self.W_zero = []
        self.W_one = []
        self.L = []
        self.G = []
        self.Reward = []
        self.Theta = []
        self.numPara = 0
        self.weight_decay = weight_decay
        self.alpha = alpha

        for group in self.param_groups:
            for p in group['params']:
                self.W1.append(p.data.clone())
                self.W_zero.append(p.data.clone().zero_())
                self.W_one.append(p.data.clone().fill_(1))
                self.L.append(p.data.clone().fill_(1))
                self.G.append(p.data.clone().zero_())
                self.Reward.append(p.data.clone().zero_())
                self.Theta.append(p.data.clone().zero_())
                self.numPara = self.numPara + 1

    def step(self, closure=None):
        """Performs a single optimization step.
        Arguments:
            closure (callable, optional): A closure that reevaluates the model
                and returns the loss.
        """
        loss = None
        if closure is not None:
            loss = closure()

        pind = 0
        for group in self.param_groups:
            for p in group['params']:
                if p.grad is None:
                    continue
                grad = p.grad.data + self.weight_decay * p.data
                self.L[pind] = self.L[pind].max(grad.abs())
                self.G[pind] = self.G[pind] + grad.abs()
                self.Reward[pind] = (self.Reward[pind] - (p.data - self.W1[pind]).mul(grad)).max(self.W_zero[pind])
                self.Theta[pind] = self.Theta[pind] + grad
                Beta = self.Theta[pind].div((self.alpha * self.L[pind]).max(self.G[pind] + self.L[pind])).div(
                    self.L[pind])
                p.data = self.W1[pind] - Beta.mul(self.L[pind] + self.Reward[pind])
                pind = pind + 1

        return loss


import torch.optim as optim
import torch


###########################################################################
# Training Deep Networks without Learning Rates Through Coin Betting
# Paper: https://arxiv.org/abs/1705.07795
#
# NOTE: This optimizer is hardcoded to run on GPU, needs to be parametrized
###########################################################################

class COCOB_Backprop(optim.Optimizer):

    def __init__(self, params, alpha=100, epsilon=1e-8, weight_decay=0):

        self._alpha = alpha
        self.epsilon = epsilon
        self.weight_decay = weight_decay
        defaults = dict(alpha=alpha, epsilon=epsilon)
        super(COCOB_Backprop, self).__init__(params, defaults)

    def step(self, closure=None):

        loss = None

        if closure is not None:
            loss = closure()

        for group in self.param_groups:
            for p in group['params']:
                if p.grad is None:
                    continue

                grad = p.grad.data + self.weight_decay * p.data
                state = self.state[p]

                if len(state) == 0:
                    state['gradients_sum'] = torch.zeros_like(p.data).to(device).float()
                    state['grad_norm_sum'] = torch.zeros_like(p.data).to(device).float()
                    state['L'] = self.epsilon * torch.ones_like(p.data).to(device).float()
                    state['tilde_w'] = torch.zeros_like(p.data).to(device).float()
                    state['reward'] = torch.zeros_like(p.data).to(device).float()

                gradients_sum = state['gradients_sum']
                grad_norm_sum = state['grad_norm_sum']
                tilde_w = state['tilde_w']
                L = state['L']
                reward = state['reward']

                zero = torch.zeros((1,)).to(device)

                L_update = torch.max(L, torch.abs(grad))
                gradients_sum_update = gradients_sum + grad
                grad_norm_sum_update = grad_norm_sum + torch.abs(grad)
                reward_update = torch.max(reward - grad * tilde_w, zero)
                new_w = -gradients_sum_update / (
                            L_update * (torch.max(grad_norm_sum_update + L_update, self._alpha * L_update))) * (
                                    reward_update + L_update)
                p.data = p.data - tilde_w + new_w
                tilde_w_update = new_w

                state['gradients_sum'] = gradients_sum_update
                state['grad_norm_sum'] = grad_norm_sum_update
                state['L'] = L_update
                state['tilde_w'] = tilde_w_update
                state['reward'] = reward_update

        return loss
