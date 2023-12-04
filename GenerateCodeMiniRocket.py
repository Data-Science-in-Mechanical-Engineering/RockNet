import numpy as np
from sympy.utilities.iterables import multiset_permutations
import math

from jinja2 import Template, Environment, FileSystemLoader

def generate_kernels():
    k = np.array([1, 1, 1, 0, 0, 0, 0, 0, 0])

    kernel_bin = []
    for e in multiset_permutations(k):
        kernel_bin.append(0)
        for i in range(9):
            kernel_bin[-1] += 2**i * e[i]

    return np.array(kernel_bin)


def generate_dilations(len_timeseries):
    max_val = int(min(math.log2((len_timeseries-1) / 8), 32))
    return np.array([2**i for i in range(max_val + 1)])


def quantiles(n):
    return np.array([((_ * ((np.sqrt(5) + 1) / 2)) % 1) for _ in range(1, n + 1)], dtype=np.float32)


# def generate_dataset():

def generate_matrix_code(matrix, use_float):
    data = "{"
    if len(matrix.shape) == 1:
        for i in range(len(matrix)):
            data += f"{float(matrix[i]) if use_float else int(matrix[i])}, "
    else:
        for i in range(len(matrix)):
            data += f"{generate_matrix_code(matrix[i])}, "
    return data[0:-1] + "}"


def generate_code(dataset, kernels, dilations, num_biases_per_kernel, quantiles):
    jinja_environment = Environment(loader=FileSystemLoader('c_src/jinja_templates'))
    template_rocket_config_h = jinja_environment.get_template('rocket_config.h.jinja')
    template_rocket_config_c = jinja_environment.get_template('rocket_config.c.jinja')

    template_values = {
        'length_time_series': len(dataset[0][0]),
        'num_time_series': len(dataset[0]),
        'num_kernels': len(kernels),
        'num_dilations': len(dilations),
        'num_biases_per_kernel': num_biases_per_kernel,
        'timeseries_data': [generate_matrix_code(m, use_float=True) for m in dataset[0]],
        'labels': generate_matrix_code(dataset[1], use_float=True),
        'kernels': generate_matrix_code(kernels, use_float=False),
        'dilations': generate_matrix_code(dilations, use_float=False),
        'quantiles': generate_matrix_code(quantiles, use_float=True)
    }

    output = template_rocket_config_h.render(template_values)
    with open('c_src/include/rocket_config.h', 'w') as f:
        f.write(output)

    output = template_rocket_config_c.render(template_values)
    with open('c_src/src/rocket_config.c', 'w') as f:
        f.write(output)


def generate_data(len_timeseries):
    """data = np.random.randn(50, len_timeseries)
    data[0:50, :] = np.random.randn(50, len_timeseries) * 0.9
    label = np.ones((len(data), ))
    label[0:50] = -1.0"""

    num_data = 1000

    data = np.zeros((num_data, len_timeseries))
    label = np.ones((num_data,))
    for i in range(num_data // 2):
        data[i, :] = np.sin(np.array([j/len_timeseries * 15 * np.pi for j in range(len_timeseries)]) + np.random.randn(1)*np.pi)
        label[i] = 1.0

    for i in range(num_data // 2, num_data):
        data[i, :] = np.sin(np.array([j/len_timeseries * 2 * np.pi for j in range(len_timeseries)]) + np.random.randn(1)*np.pi)
        label[i] = -1.0

    """data[0:50, :] = np.random.randn(50, len_timeseries) * 0.9
    label = np.ones((len(data),))
    label[0:50] = -1.0"""

    np.random.seed(1)
    shuffle_vec = np.array([i for i in range(len(data))])
    np.random.shuffle(shuffle_vec)
    data = data[shuffle_vec, :]
    label = label[shuffle_vec]
    return data, label


if __name__ == "__main__":
    len_timeseries = 101

    data, labels = generate_data(len_timeseries)

    dilations = generate_dilations(len_timeseries)
    kernels = generate_kernels()

    num_biases_per_kernel = int(10_000 / (len(dilations) * len(kernels)))

    generate_code((data, labels), kernels, dilations, num_biases_per_kernel, quantiles(len(dilations)*len(kernels)*num_biases_per_kernel))

    kernel_bins = generate_kernels()
    print(len(kernel_bins))
    for e in kernel_bins:
        print(f"{e:09b}")


