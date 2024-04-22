"""
This file implements random convolutional kernels for ROCKET. -and MiniRocket soon
"""

import jax.numpy as jnp
import jax
import equinox as eqx
from jax import jit
from functools import partial
from typing import Any


class RocketKernel(eqx.Module):
    rkey: jax.random.PRNGKey(seed=11)
    num_kernels : jnp.int32
    ppv : jax.Array
    biases : jax.Array
    dilations : jax.Array
    paddings : jax.Array
    candidate_lengths : jax.Array
    kernel_lengths : jax.Array
    weights : jax.Array
    max : jax.Array
#    feature_map : Any

    def __init__(self,
                 input_length,
                 num_kernels=1000,
                 rkey=jax.random.PRNGKey(seed=11),
                 method_selection='rocket'
                 ):
        """
        Generate kernels.
        num_kernels : Number of generated kernels. Default is 10,000 as in paper.
        rkey: random state for jax.
        """
        super().__init__()
        self.rkey = rkey
        self.num_kernels = num_kernels
        self.ppv = jnp.zeros(shape=(self.num_kernels,))
        self.biases = jnp.zeros(shape=(self.num_kernels,))
        self.dilations = jnp.zeros(shape=(self.num_kernels,), dtype=jnp.int32)
        self.paddings = jnp.zeros(shape=(self.num_kernels,), dtype=jnp.int32)

        if method_selection == 'rocket':
            self.candidate_lengths = jnp.array((7,9,11))
            self.kernel_lengths = jax.random.choice(key=self.rkey, a=self.candidate_lengths, shape=(self.num_kernels,))
            self.weights = jnp.zeros(shape=(self.kernel_lengths.sum(),))
            self.max = jnp.zeros(shape=(self.num_kernels,))
#            self.feature_map = jnp.zeros(shape=(input_length,self.num_kernels*2))

        elif method_selection == 'minirocket':
            self.candidate_lengths = jnp.array([9])
            self.kernel_lengths = jnp.repeat(self.candidate_lengths, self.num_kernels)
            self.weights = jnp.zeros(shape=(self.kernel_lengths.sum(),))
#            self.feature_map = jnp.zeros(shape=self.num_kernels,)

        else:
            print('Invalid Method! Killing process')
            exit()

        start_idx = 0

        for i in range (num_kernels):

            if method_selection == 'rocket':
                _length = self.kernel_lengths[i]
                _weights = jax.random.normal(key=self.rkey, shape=(_length,))

                end_idx = start_idx + _length

                self.weights = self.weights.at[start_idx:end_idx].set(_weights - _weights.mean())

                self.biases = self.biases.at[i].set(jax.random.uniform(key=self.rkey, minval=-1, maxval=1))

                dil = 2 ** jax.random.uniform(key=self.rkey, minval=0, maxval=jnp.log2((input_length - 1) / (_length - 1)))
                self.dilations = self.dilations.at[i].set(dil)

                if jax.random.bernoulli(key=self.rkey, p=0.5):
                    self.paddings = self.paddings.at[i].set((_length-1)*self.dilations[i] // 2)

            elif method_selection == 'minirocket':
                _alpha = -1
                _beta = 2

                # weights contain -1, 2 in different positions such that kernel sum == 0, implement WIP
                # other stuff depend on convolution output with input X
                pass

            start_idx = end_idx


# Applies single kernel to the input.
    @partial(jit, static_argnums=(1,2,3,4,5,6))
#   def apply_single_kernel(self, X_tuple, w_begin_idx, w_end_idx, kernel_idx):
    def apply_single_kernel(self, X_tuple, kernel_length, bias, dilation, padding, weights):
        """
        kernel_length = self.kernel_lengths[kernel_idx]
        bias = self.biases[kernel_idx]
        dilation = self.dilations[kernel_idx]
        padding = self.dilations[kernel_idx]
        weights = self.weights[w_begin_idx:w_end_idx]
        """
        input_length = len(X_tuple)
        output_length = input_length + 2 * padding - dilation * (kernel_length - 1)
        _ppv = 0
        _max = -jnp.inf

        ending_index = input_length + padding - dilation * (kernel_length - 1)

        for i in range(-padding, ending_index):  # iterate over the input

            _sum = bias
            index = i

            for j in range(kernel_length):  # for each kernel do the sum

                if index > -1 and index < input_length:
                    _sum = _sum + weights[j] * X_tuple[index]

                index = index + dilation

        # Update features max and ppv.

            if _sum > _max:
                _max = _sum

            if _sum > 0:
                _ppv += 1

        return _ppv / output_length, _max

    def __call__(self, X):

        """
        Apply all kernels to the input.
        X is the input, which contains the time series for all examples.
        """

        num_examples, _ = X.shape
        features = jnp.empty(shape=(num_examples,self.num_kernels*2))

        for ex_idx in range(num_examples):

            a1 = 0
            a2 = 0

# jit expects hashable arguments, therefore convert the input to a tuple and pass like that
            X_tuple = tuple(map(float, X[ex_idx]))
            for kernel_idx in range(self.num_kernels):

                b1 = a1 + int(self.kernel_lengths[kernel_idx])
                b2 = a2 + 2

#               Call the apply kernels func to fill up the feature map.
#               self.feature_map = self.feature_map.at[ex_idx, a2:b2].set(self.apply_single_kernel(X_tuple=X_tuple,w_begin_idx=a1,w_end_idx=b1,kernel_idx=kernel_idx))
                w_tuple = tuple(map(float, self.weights[a1:b1]))

                features = features.at[ex_idx, a2:b2].set(self.apply_single_kernel(X_tuple=X_tuple,
                                                         kernel_length = int(self.kernel_lengths[kernel_idx]),
                                                         bias = float(self.biases[kernel_idx]),
                                                         dilation = int(self.dilations[kernel_idx]),
                                                         padding = int(self.paddings[kernel_idx]),
                                                         weights = w_tuple))



                a1 = b1
                a2 = b2

        return features

"""
# Dummy Input
new = RocketKernel(input_length=10)
dummy_input = jax.random.uniform(shape=(10,10), key=jax.random.PRNGKey(seed=123))
new(X=dummy_input)
print(new.feature_map[:10, :30])
print(new.feature_map.shape)
"""