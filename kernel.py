"""
This file implements random convolutional kernels for ROCKET. -and MiniRocket soon
"""

import jax.numpy as jnp
import jax
from jax import jit

class RocketKernel():

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
        self.weights = jnp.zeros(shape=(self.kernel_lengths.sum(),))
        self.biases = jnp.zeros(shape=(self.num_kernels,))
        self.dilations = jnp.zeros(shape=(self.num_kernels,))
        self.paddings = jnp.zeros(shape=(self.num_kernels,))

        if method_selection == 'rocket':
            self.candidate_lengths = jnp.array((7,9,11))
            self.kernel_lengths = jax.random.choice(key=self.rkey, a=self.candidate_lengths, shape=(self.num_kernels,1))
            self.max = jnp.zeros(shape=(self.num_kernels,))

        elif method_selection == 'minirocket':
            self.candidate_lengths = jnp.array([9])
            self.kernel_lengths = jnp.repeat(self.candidate_lengths, self.num_kernels)

        else:
            print('Invalid Method! Killing process')
            exit()

        start_idx = 0

        for i in range (num_kernels):

            if method_selection == 'rocket':
                _length = self.kernel_lengths[i].squeeze()
                _weights = jax.random.normal(key=self.rkey, shape=(_length,))

                end_idx = start_idx + _length

                self.weights = self.weights.at[start_idx:end_idx].set(_weights - _weights.mean())

                self.biases = self.biases.at[i].set(jax.random.uniform(key=self.rkey, minval=-1, maxval=1))

                dil = 2 ** jax.random.uniform(key=self.rkey, minval=0, maxval=jnp.log2((input_length - 1) / (_length - 1)))
                self.dilations = self.dilations.at[i].set(jnp.int32(dil))

                if jax.random.bernoulli(key=self.rkey, p=0.5):
                    self.paddings = self.paddings.at[i].set((_length-1)*self.dilations[i] // 2)

            elif method_selection == 'minirocket':
                pass

            start_idx = end_idx


# Applies single kernel to the input.

    def apply_single_kernel(self, X, weights, kernel_length, bias, dilation, padding):

        input_length = len(X)
        output_length = input_length + 2 * padding - dilation * (kernel_length - 1)
        _ppv = 0
        _max = -jnp.inf

        ending_index = input_length + padding - dilation * (kernel_length - 1)

        for i in range(int(-padding), int(ending_index)):  # iterate over the input

            _sum = bias
            index = i

            for j in range(kernel_length):  # for each kernel do the sum

                if index > -1 and index < input_length:
                    _sum = _sum + weights[j] * X[index]

                index = index + int(dilation)

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
        _X is the generated feature map containing ppv and max values.
        """

        num_examples, _ = X.shape
        self.feature_map = jnp.zeros(shape=(num_examples, self.num_kernels * 2))

        for ex_idx in range(num_examples):

            a1 = 0
            a2 = 0

            for kernel_idx in range(self.num_kernels):

                b1 = a1 + self.kernel_lengths[kernel_idx].squeeze()
                b2 = a2 + 2

                """
                Call the apply kernels func to fill up the feature map.
                """

                self.feature_map = self.feature_map.at[ex_idx, a2:b2].set(self.apply_single_kernel(X[ex_idx], self.weights[a1:b1],
                                                                      self.kernel_lengths[kernel_idx].squeeze(), self.biases[kernel_idx],
                                                                      self.dilations[kernel_idx], self.paddings[kernel_idx]))

                a1 = b1
                a2 = b2



# Dummy Input
'''''''''
new = RocketKernel(input_length=10)
dummy_input = jax.random.uniform(shape=(10,10), key=jax.random.PRNGKey(seed=123))
new(X=dummy_input)
print(new.feature_map[:10, :30])
print(new.feature_map.shape)
'''
