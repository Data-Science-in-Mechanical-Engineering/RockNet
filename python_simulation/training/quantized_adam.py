from functools import partial
import equinox as eqx
import jax
import jax.numpy as jnp
import math


# functions for quantization aware training (QAT)
@jax.custom_jvp
def quantization_round(x):
    return jnp.round(x)

@quantization_round.defjvp
def quantization_round_jvb(primals, tangents):
    return quantization_round(primals[0]), tangents[0]


def param_quantize(x, scaling, bits=8):
    if x is None:
        return None
    x = x / scaling
    max_val_quant = (2 ** (bits - 1)) - 1
    x = jnp.clip(quantization_round(x * max_val_quant), -max_val_quant, max_val_quant)
    return x

def param_dequantize(x, scaling, bits=8):
    if x is None:
        return None
    return x / ((2 ** (bits - 1)) - 1) * scaling

def param_calculate_scaling(x):
    if x is None:
        return None
    return jnp.max(jnp.abs(x))

def quantize_graph(graph, bits=8):
    params, _ = eqx.partition(graph, eqx.is_array)
    scalings = jax.tree_util.tree_map(param_calculate_scaling, params)
    return jax.tree_util.tree_map(partial(param_quantize, bits=bits), params, scalings), scalings 

def dequantize_graph(graph, scalings, bits=8):
    params, _ = eqx.partition(graph, eqx.is_array)
    return jax.tree_util.tree_map(partial(param_dequantize, bits=bits), params, scalings)


def generate_dynamic_tree_quantization_fn():
    values = [i for i in range(0, 2**8)]

    quantized_values = []
    for v in values:
        sign = 1
        if v >> 7 == 1:
            sign = -1
        exponent = 0
        mask = 1<<6
        while v & mask == 0 and exponent < 7:
            exponent += 1
            mask >>= 1
        scaling = 10 ** (-exponent)
        mantissa = ((v & (int(round(2**(6-exponent))) - 1))) / (2**(6-exponent)-1 + 1e-7)

        quantized_values.append(sign * mantissa * scaling)

    quantized_values = jnp.array(quantized_values)

        

    # print(jnp.unique(boundaries).shape)

    # print(boundaries)
    # import matplotlib.pyplot as plt

    # plt.hist(boundaries, bins=10)
    # plt.xlabel('Value')
    # plt.ylabel('Frequency')
    # plt.title('Histogram of Boundaries')
    # plt.show()

    def get_dequantized_value(v):
        return quantized_values[v]
    
    def get_quantized_value(v):
        dists = jnp.abs(v - quantized_values)
        return jnp.argmin(dists)
    
    def append_zeros_and_tile(x):
        num_appended_zeros = 0
        if x.shape[0] % 256 != 0:
            num_appended_zeros = 256 - x.shape[0] % 256
            x = jnp.concatenate([x, jnp.zeros((num_appended_zeros,))])

        num_tiles = x.shape[0] // 256
        x = jnp.reshape(x, (num_tiles, 256))
        return x, num_appended_zeros
    
    def param_quantize(x, scaling):
        if x is None:
            return None
        original_shape = x.shape
        x = x.flatten()
        x, num_appended_zeros = append_zeros_and_tile(x)

        x = jax.vmap(lambda i,s: i/s)(x, scaling)
        x = x.flatten()
        x = x[0:len(x)-num_appended_zeros]
        x = jax.vmap(get_quantized_value)(x)
        return jnp.reshape(x, original_shape)
    
    def param_dequantize(x, scaling):
        if x is None:
            return None
        original_shape = x.shape
        x = x.flatten()
        x = jax.vmap(get_dequantized_value)(x)

        x, num_appended_zeros = append_zeros_and_tile(x)
        x = jax.vmap(lambda i,s: i*s)(x, scaling)
        x = x.flatten()
        x = x[0:len(x)-num_appended_zeros]

        return jnp.reshape(x, original_shape)

    def param_calculate_scaling_tile(x):
        if x is None:
            return None
        x = x.flatten()
        if x.shape[0] % 256 != 0:
            x = jnp.concatenate([x, jnp.zeros(256 - x.shape[0] % 256)])

        num_tiles = x.shape[0] // 256
        x = jnp.reshape(x, (num_tiles, 256))

        scalings = jnp.max(jnp.abs(x), axis=1)
        return scalings
    
    def quantize_graph(graph):
        params, _ = eqx.partition(graph, eqx.is_array)
        scalings = jax.tree_util.tree_map(param_calculate_scaling_tile, params)
        return jax.tree_util.tree_map(partial(param_quantize), params, scalings), scalings 

    def dequantize_graph(graph, scalings):
        params, _ = eqx.partition(graph, eqx.is_array)
        return jax.tree_util.tree_map(partial(param_dequantize), params, scalings)

    #for i in [-1 + i * 0.001 for i in range(0, 2001)]:
        # print(i - get_dequantized_value(get_quantized_value(i)))
    
    return quantize_graph, dequantize_graph

if __name__ == "__main__":
    generate_dynamic_tree_quantization_fn()


def m_update(grad, m, beta1_t):
    if grad is None:
        return None
    else:
        return (1 - beta1_t) * grad + beta1_t * m
    
def v_update(grad, v, beta2_t):
    if grad is None:
        return None
    else:
        return (1 - beta2_t) * grad ** 2 + beta2_t * v
    
def m_hat_update(m, beta1_t):
    if m is None:
        return None
    return m / (1 - beta1_t)

def v_hat_update(v, beta2_t):
    if v is None:
        return None
    return v / (1 - beta2_t)

def x_update(m_hat, v_hat, learning_rate_t, epsilon):
    if m_hat is None:
        return None
    return - learning_rate_t * m_hat / (jnp.sqrt(v_hat + 0.0) + epsilon)


class QuantizedAdam:
    def __init__(self, learning_rate, use_dynamic_tree_quantization=True, num_bits=8, beta1=0.9, beta2=0.999, epsilon=1e-8, weight_decay=0.0001):
        self.__learning_rate = learning_rate
        self.__beta1 = beta1
        self.__beta2 = beta2
        self.__epsilon = epsilon

        self.__num_bits = num_bits

        if num_bits == 8 and use_dynamic_tree_quantization:
            self.__quantize, self.__dequantize = generate_dynamic_tree_quantization_fn()
        else:
            self.__quantize = partial(quantize_graph, bits=num_bits)
            self.__dequantize = partial(dequantize_graph, bits=num_bits)


    def init(self, params):
        return {"m": jax.tree_util.tree_map(lambda x: jnp.zeros(x.shape), params), 
                "v": jax.tree_util.tree_map(lambda x: jnp.zeros(x.shape), params),
                "t": jnp.zeros((1,))}
        

    def update(self, grads, opt_state, params):
        t = opt_state["t"] + 1

        beta1_t = self.__beta1 ** t
        beta2_t = self.__beta2 ** t
        learning_rate_t = self.__learning_rate

        m_t = jax.tree_util.tree_map(partial(m_update, beta1_t=self.__beta1), grads, opt_state["m"])
        v_t = jax.tree_util.tree_map(partial(v_update, beta2_t=self.__beta2), grads, opt_state["v"])

        m_hat_t = jax.tree_util.tree_map(partial(m_hat_update, beta1_t=beta1_t), m_t)
        v_hat_t = jax.tree_util.tree_map(partial(v_hat_update, beta2_t=beta2_t), v_t)

        params_update = jax.tree_util.tree_map(partial(x_update, learning_rate_t=learning_rate_t, epsilon=self.__epsilon), m_hat_t, v_hat_t) 
        # new_params, _ = eqx.partition(new_params, eqx.is_array)
        
        # quantize forward backward to simulate quantization error.
        m_t = self.__quantize(m_t)
        v_t = self.__quantize(v_t)

        m_t = self.__dequantize(graph=m_t[0], scalings=m_t[1])
        v_t = self.__dequantize(graph=v_t[0], scalings=v_t[1])

        
        return params_update, {"m": m_t, 
                         "v": v_t, "t": t}