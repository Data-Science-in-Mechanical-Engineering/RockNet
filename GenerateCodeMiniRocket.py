import copy
from pathlib import Path

import numpy as np
from sympy.utilities.iterables import multiset_permutations
import math

from jinja2 import Template, Environment, FileSystemLoader

import pandas as pd
import shutil

import matplotlib.pyplot as plt

def calculate_num_rounds(num_messages):
	base_num_rounds = 150
	return max(3 * num_messages, base_num_rounds)


def calculate_round_time(message_size, num_messages):
	base_num_rounds = 150
	num_rounds = calculate_num_rounds(num_messages)
	T_slot = calculate_slot_time(message_size, num_messages)
	return T_slot*num_rounds / 1000


def calculate_slot_time(message_size, num_messages):
	S_v = math.ceil(num_messages/8)
	S = 12 + 2*S_v + message_size
	T_a = (440+4*S)*1.037  # 4 us for BLW, 32 for IEEE 802.15.4
	T_p = 600 + (26+0.155*(S_v+message_size))*num_messages+1.8*S
	T_slot = max(T_a, T_p)
	return T_slot


def calculate_num_messages(message_size, message_list):
	num_messages = 0
	for m in message_list:
		num_messages += math.ceil(m / message_size - 1e-6)
	return num_messages + 1 # because of initator message


def get_min(arr):
	min_value = arr[0]
	min_ind = 0
	for i in range(1, len(arr)):
		if min_value > arr[i]:
			min_ind = i
			min_value = arr[i]

	return min_ind, min_value


def generate_node_array(name, id_nodes):
	code = f"static const uint8_t {name}[] = {{"
	for idn in id_nodes:
		code += f"{idn}, "
	code = code[:-2]

	code += "};\n"
	return code


def generate_timing_configuration(message_size, num_devices):
	mixer_size = message_size
	i = 1
	while mixer_size > 100:
		mixer_size = int(message_size // i)
		if mixer_size * i < message_size:
			mixer_size += 1
		i += 1

	message_list = [message_size for _ in range(num_devices)]

	num_messages = calculate_num_messages(mixer_size, message_list)

	num_rounds = calculate_num_rounds(num_messages)

	slot_time = calculate_slot_time(mixer_size, num_messages)

	"""sizes = [i for i in range(1, 200)]
	num_messages = [calculate_num_messages(s, message_list) for s in sizes]
	round_times = [calculate_round_time(sizes[i], num_messages[i]) for i in range(len(sizes))]
	num_rounds = [calculate_num_rounds(num_messages[i]) for i in range(len(sizes))]
	slot_times = [calculate_slot_time(sizes[i], num_messages[i]) for i in range(len(sizes))]"""

	# best_ind, best_time = get_min(round_times)
	slot_length = round(slot_time) + 10  # plus 10 to have a bit of security gap
	round_length = round(slot_length / 1000 * num_rounds) + 150 + 20
	code = f"#define MX_PAYLOAD_SIZE {mixer_size}\n"
	code += f"#define MX_ROUND_LENGTH {num_rounds}\n"
	code += f"#define MX_SLOT_LENGTH GPI_TICK_US_TO_HYBRID2({slot_length})\n"
	code += f"#define ROUND_LENGTH_MS                 {round_length}\n"

	code += f"#define MX_GENERATION_SIZE {num_messages}\n"

	return code


def generate_rocket_mixer_config(code_path, num_devices, num_total_nodes, len_time_series):
	# generate code for nodes
	code_dnni_config_h = "#ifndef INC_DNNI_CONFIG_H\n#define INC_DNNI_CONFIG_H\n"

	code_dnni_config_h += "\ntypedef struct message_assignment_t_tag \n" \
						  "{ \n" \
						  "	uint8_t id;   // id of message slot \n" \
						  "	uint16_t size;  // slot size in byte \n" \
						  "	uint16_t mixer_assignment_start;  // the index in mixer, the message starts \n" \
						  "	uint16_t mixer_assignment_end;   // the index in mixer the message ends (not including this index)\n" \
						  "	uint16_t size_end; // the size of the piece of the message in the mixer message at index mixer_assignment_end-1 \n" \
						  "} message_assignment_t;\n\n"

	id_devices = [i + 1 for i in range(num_devices)]
	id_relays = [i + num_devices for i in range(num_total_nodes - num_devices + 1)]
	code_dnni_config_h += generate_node_array("nodes", id_devices + id_relays)
	code_dnni_config_h += generate_node_array("dnni_nodes", id_devices)

	header_message_size = 2
	metadata_message = header_message_size + 2
	bytes_activations_sent = len_time_series * 4
	layer_message_size = max(metadata_message, header_message_size + bytes_activations_sent)

	code_dnni_config_h += "\nstatic message_assignment_t message_assignment[] = {\n"
	for idd in [1]:
		code_dnni_config_h += f"	{{.id={idd}, .size={layer_message_size}}},\n "
	code_dnni_config_h = code_dnni_config_h[0:-3]
	code_dnni_config_h += "};\n"

	# calculate timing configurations
	code_dnni_config_h += generate_timing_configuration(message_size=layer_message_size, num_devices=num_devices)

	code_dnni_config_h += "\n#endif /* INC_DNNI_CONFIG_H */\n"
	with open(f"{code_path}/rocket_mixer_config.h", 'w') as f:
		f.write(code_dnni_config_h)


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


def split_kernels(num_nodes, num_kernels):
	"""
	Splits the neurons across multiple nodes.

	Returns
	-------
		split: List(int) list containing the number of neurons for each device.
	"""
	split = [num_kernels // num_nodes for _ in range(num_nodes)]
	i = 0
	while i < num_kernels % num_nodes:
		split[i] += 1
		i += 1

	return split


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


def quantize_8_bit(data, offset, scaling):
	return np.clip((data - offset) / scaling * 127, a_min=-127, a_max=127)


def generate_code(dataset_training, dataset_evaluation, kernels, dilations, num_biases_per_kernel, quantiles, quantize):
	jinja_environment = Environment(loader=FileSystemLoader('c_src/jinja_templates'))
	template_rocket_config_h = jinja_environment.get_template('rocket_config.h.jinja')
	template_rocket_config_c = jinja_environment.get_template('rocket_config.c.jinja')

	if quantize:
		quantization_offset = np.mean(dataset_training[0])
		quantization_scaling = np.percentile(np.abs(dataset_training[0] - quantization_offset), q=99.9)

		dataset_training[0] = quantize_8_bit(dataset_training[0], quantization_offset, quantization_scaling)
		dataset_evaluation[0] = quantize_8_bit(dataset_evaluation[0], quantization_offset, quantization_scaling)

	num_classes = int(round(max(dataset_training[1])))

	template_values = {
		'time_series_type_t': "int8_t" if quantize else "float",
		'length_time_series': len(dataset_training[0][0]),
		'num_training_time_series': len(dataset_training[0]),
		'num_evaluation_time_series': len(dataset_evaluation[0]),
		'num_kernels': len(kernels),
		'num_dilations': len(dilations),
		'num_biases_per_kernel': num_biases_per_kernel,
		'training_timeseries_data': [generate_matrix_code(m, use_float=not quantize) for m in dataset_training[0]],
		'training_labels': generate_matrix_code(dataset_training[1] - 1, use_float=False),
		'evaluation_labels': generate_matrix_code(dataset_evaluation[1] - 1, use_float=False),
		'evaluation_timeseries_data': [generate_matrix_code(m, use_float=not quantize) for m in dataset_evaluation[0]],
		'training_labels_training_evaluation': generate_matrix_code(dataset_evaluation[1] - 1, use_float=False),
		'kernels': generate_matrix_code(kernels, use_float=False),
		'dilations': generate_matrix_code(dilations, use_float=False),
		'quantiles': generate_matrix_code(quantiles, use_float=True),
		'quantiles': generate_matrix_code(quantiles, use_float=True),
		'num_classes': num_classes,
		'batch_size': 128
	}

	output = template_rocket_config_h.render(template_values)
	with open('c_src/include/rocket_config.h', 'w') as f:
		f.write(output)

	output = template_rocket_config_c.render(template_values)
	with open('c_src/src/rocket_config.c', 'w') as f:
		f.write(output)

	"""files = ["rocket_config.h", "rocket_config.c", "conv.h", "linear_classifier.h", "conv.c", "linear_classifier.c"]
	for f in files:
		shutil.copy(f"c_src/{'src' if f[-1] == 'c' else 'include'}/{f}", "c_src/cp_firmware/app/")"""

	generate_rocket_mixer_config(code_path="c_src/cp_firmware/app/",
								 num_devices=2,
								 num_total_nodes=2,
								 len_time_series=len_timeseries)


def simulate_linear_system(A, C, x0, length, noise):
	Y = np.zeros((length, ))
	Y[0] = C @ x0
	x = copy.deepcopy(x0)
	for i in range(1, length):
		x = A@x+np.random.randn(*x0.shape)*noise
		Y[i] = C@x

	return Y

def generate_matrix(dim):
	A = np.random.randn(dim, dim)
	while not np.all(np.abs(np.linalg.eig(A)[0]) < 1):
		A = np.random.randn(dim, dim)
	return A

def generate_data(len_timeseries):
	"""data = np.random.randn(50, len_timeseries)
	data[0:50, :] = np.random.randn(50, len_timeseries) * 0.9
	label = np.ones((len(data), ))
	label[0:50] = -1.0"""

	"""table = pd.read_table("/home/alex/Downloads/UCRArchive_2018/FordA/FordA_TRAIN.tsv", header=None)

	labels = np.array(table.iloc[:, 0])
	data = np.array(table.iloc[:, 1:])
	return data, labels"""

	num_data = 40000
	np.random.seed(1000)
	A1 = generate_matrix(5)
	print(np.linalg.eig(A1)[0])
	C1 = np.random.randn(1, 5)

	A2 = A1 * 0.5  #generate_matrix(5)
	C2 = 2.1*C1  #np.random.randn(1, 5)

	x0 = 10*np.random.randn(5, num_data//2+1)

	data = np.zeros((num_data, len_timeseries))
	label = np.ones((num_data,))
	for i in range(num_data // 2):
		data[i, :] = np.sin(np.array([j/len_timeseries * 15 * np.pi for j in range(len_timeseries)]) + np.random.randn(1)*np.pi)
		label[i] = 1

	j = 0
	for i in range(num_data // 2, num_data):
		data[i, :] = np.sin(np.array([j/len_timeseries * 14 * np.pi for j in range(len_timeseries)]) + np.random.randn(1)*np.pi)
		label[i] = 2

	"""data[0:50, :] = np.random.randn(50, len_timeseries) * 0.9
	label = np.ones((len(data),))
	label[0:50] = -1.0"""



	np.random.seed(1)
	shuffle_vec = np.array([i for i in range(len(data))])
	np.random.shuffle(shuffle_vec)
	data = data[shuffle_vec, :]
	label = label[shuffle_vec]
	return data, label


def load_ucr_dataset(name, test=False):
	data = copy.deepcopy(
		pd.read_csv(f"{Path.home()}/datasets/{name}/{name}_{'TRAIN' if not test else 'TEST'}.tsv", sep="\t",
					header=None))

	# remove NANs by interpolation
	data = data.interpolate(axis=1)

	X = np.array(data[data.columns[1:]])
	y = np.array(data[data.columns[0]])

	# shuffle data
	shuffle_vec = np.array([i for i in range(len(y))])
	np.random.shuffle(shuffle_vec)

	X = X[shuffle_vec, :]
	X -= np.mean(X)
	X /= np.std(X)
	y = y[shuffle_vec]

	return np.array(X, dtype=np.float32), np.array(y, dtype=np.int64)


def generate_data_ucr(num_trajectories, name_dataset, test):
	X_train, y_train = load_ucr_dataset(name_dataset, test=test)

	num_trajectories = min(num_trajectories, len(X_train))

	return (np.array(X_train[0:num_trajectories], dtype=np.float32),
			np.array(y_train[0:num_trajectories], dtype=np.int64))

if __name__ == "__main__":
	len_timeseries = 101
	num_nodes = 2
	quantize = False

	#ädata, labels = generate_data(len_timeseries, quantize)
	np.random.seed(1)
	data_train, labels_train = generate_data_ucr(num_trajectories=2200, name_dataset="ElectricDevices", test=False)
	data_test, labels_test = generate_data_ucr(num_trajectories=200, name_dataset="ElectricDevices", test=True)

	len_timeseries = len(data_train[0])

	dilations = generate_dilations(len_timeseries)
	kernels = generate_kernels()

	num_biases_per_kernel = int(10_000 / (len(dilations) * len(kernels)))

	generate_code([data_train, labels_train], [data_test, labels_test], kernels, dilations, num_biases_per_kernel,
				  quantiles(len(dilations)*len(kernels)*num_biases_per_kernel), quantize=True)

	kernel_bins = generate_kernels()

	print(len(kernel_bins))
	for e in kernel_bins:
		print(f"{e:09b}")


