import numpy as np
from sympy.utilities.iterables import multiset_permutations
import math

from jinja2 import Template, Environment, FileSystemLoader

import pandas as pd
import shutil

from pathlib import Path
import copy

import math


def calculate_slot_time(message_size_total, num_messages):
	MX_SLOT_LENGTH = 80000  # initial value for iterative approach, in ticks
	RX_TO_GRID_OFFSET = 40 * 16  # ticks
	ISR_LATENCY_BUFFER = 20 * 16  # ticks
	MX_GENERATION_SIZE = num_messages
	MX_PAYLOAD_SIZE = message_size_total  # B
	PHY_PAYLOAD_SIZE = 2 + 1 + 1 + 2 * math.ceil(MX_GENERATION_SIZE / 8) + MX_PAYLOAD_SIZE  # B
	PACKET_AIR_TIME = ((2 + 4 + 2 + PHY_PAYLOAD_SIZE + 3) * 4) * 16  # ticks
	JITTER_TOLERANCE = 4 * 16  # ticks

	while True:
		DRIFT_TOLERANCE = min(2500, max(math.ceil(MX_SLOT_LENGTH / 1000), 1))  # ticks
		RX_WINDOW_MIN = 2 * ((3 * DRIFT_TOLERANCE) + (2 * JITTER_TOLERANCE) + 5 * 16)  # ticks
		RX_WINDOW_INCREMENT = (3 * DRIFT_TOLERANCE) / 2  # ticks
		RX_WINDOW_MAX = min(RX_WINDOW_MIN + (20 * RX_WINDOW_INCREMENT),
							(MX_SLOT_LENGTH - PACKET_AIR_TIME - RX_TO_GRID_OFFSET - ISR_LATENCY_BUFFER) / 2)

		min_len_slot = (PACKET_AIR_TIME + RX_TO_GRID_OFFSET + 2 * RX_WINDOW_MAX + ISR_LATENCY_BUFFER + 25 * 16) * 1.0003

		if min_len_slot == MX_SLOT_LENGTH:
			break
		else:
			MX_SLOT_LENGTH = min_len_slot

	# print(
	#	f'Slot time for {num_messages} msgs of {message_size} B (BLE 2M): {math.ceil(MX_SLOT_LENGTH / 16)} us (MX_SLOT_LENGTH = {math.ceil(MX_SLOT_LENGTH)})')

	return math.ceil(MX_SLOT_LENGTH / 16)


def calculate_num_rounds(num_messages):
	base_num_rounds = 150
	return max(3 * num_messages, base_num_rounds)


def calculate_round_time(message_size, num_messages, agg_size):
	base_num_rounds = 150
	num_rounds = calculate_num_rounds(num_messages)
	T_slot = calculate_slot_time(message_size + agg_size, num_messages)
	return T_slot * num_rounds / 1000


def calculate_num_messages(message_size, message_list):
	num_messages = 0
	for m in message_list:
		num_messages += math.ceil(m / message_size - 1e-6)
	return num_messages + 1  # because of initator message


def generate_node_array(name, id_nodes):
	code = f"static const uint8_t {name}[] = {{"
	for idn in id_nodes:
		code += f"{idn}, "
	code = code[:-2]

	code += "};\n"
	return code


def generate_timing_configuration(message_size_list, num_devices, num_classes, agg_size):
	"""mixer_size = max(message_size_list)
	message_size_max = max(message_size_list)
	i = 1
	while mixer_size > 100:
		mixer_size = int(message_size_max // i)
		if mixer_size * i < message_size_max:
			mixer_size += 1
		i += 1

	num_messages = calculate_num_messages(mixer_size, message_size_list)

	num_rounds = calculate_num_rounds(num_messages)

	slot_time = calculate_slot_time(mixer_size, num_messages)"""
	sizes = [i for i in range(100, 200)]
	num_messages = [calculate_num_messages(s, message_size_list) for s in sizes]
	round_times = [calculate_round_time(sizes[i], num_messages[i], agg_size) for i in range(len(sizes))]
	slot_times = [calculate_slot_time(sizes[i] + agg_size, num_messages[i]) for i in range(len(sizes))]

	best_ind = np.argmin(round_times)

	slot_time = slot_times[best_ind]
	mixer_size = sizes[best_ind]
	num_rounds = calculate_num_rounds(num_messages[best_ind])
	num_messages_best = num_messages[best_ind]

	slot_length = round(slot_time) + 10  # plus 10 to have a bit of security gap
	calculation_duration = 300  #int(340 * num_classes / num_devices) + 20

	return mixer_size, num_rounds, slot_length, calculation_duration, num_messages_best


def generate_rocket_mixer_config(num_devices, num_total_nodes, len_time_series, quantize, num_classes):
	id_devices = [i + 1 for i in range(num_devices)]
	id_relays = [i + num_devices + 1 for i in range(num_total_nodes - num_devices + 1)]

	header_message_size = 2
	timeseries_message_size = header_message_size + len_time_series * (4 if not quantize else 1) + 1 + 1
	classification_message_size = header_message_size + 4 * num_classes

	message_ids = [254] + id_devices
	message_sizes = [timeseries_message_size] + [classification_message_size] * len(id_devices)

	aggregate_flag_size = num_devices // 8
	if num_devices % 8 != 0:
		aggregate_flag_size += 1

	mx_payload_size, mx_round_length, slot_length, calculation_duration, mx_generation_size = generate_timing_configuration(
		message_size_list=[timeseries_message_size] + [classification_message_size] * len(id_devices),
		num_devices=num_devices,
		num_classes=num_classes,
		agg_size=0*(num_classes*4 + aggregate_flag_size))

	mixer_config = {
		"nodes": id_devices + id_relays,
		"dnni_nodes": id_devices,
		"message_ids": message_ids,
		"message_sizes": message_sizes,
		"mx_payload_size": mx_payload_size,
		"mx_round_length": mx_round_length,
		"slot_length": slot_length,
		"calculation_duration": calculation_duration,
		"mx_generation_size": mx_generation_size,
		"aggregate_flag_size": aggregate_flag_size*0,
		"aggregate_content_size":  0,
	}


	"""# calculate timing configurations
	code_dnni_config_h += generate_timing_configuration(
		message_size_list=[timeseries_message_size] + [classification_message_size] * len(id_devices),
		num_devices=num_devices,
		num_classes=num_classes)

	# calculate aggregate configurations
	code_dnni_config_h += generate_timing_configuration(
		message_size_list=[timeseries_message_size] + [classification_message_size] * len(id_devices),
		num_devices=num_devices,
		num_classes=num_classes)

	code_dnni_config_h += "\n#endif /* INC_DNNI_CONFIG_H */\n"""
	return mixer_config


def generate_kernels():
	k = np.array([1, 1, 1, 0, 0, 0, 0, 0, 0])

	kernel_bin = []
	for e in multiset_permutations(k):
		kernel_bin.append(0)
		for i in range(9):
			kernel_bin[-1] += 2 ** i * e[i]

	return np.array(kernel_bin)


def generate_dilations(len_timeseries):
	max_val = int(min(math.log2((len_timeseries - 1) / 8), 32))
	return np.array([2 ** i for i in range(max_val + 1)])


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

	kernel_idx = [0]
	for l in split:
		kernel_idx.append(kernel_idx[-1] + l)

	return split, kernel_idx


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


def generate_code(dataset_training, dataset_evaluation, kernels, dilations, num_biases_per_kernel, quantiles, num_nodes, quantize):
	jinja_environment = Environment(loader=FileSystemLoader('c_src/jinja_templates'))
	template_rocket_config_h = jinja_environment.get_template('rocket_config_distributed.h.jinja')
	template_rocket_config_c = jinja_environment.get_template('rocket_config_distributed.c.jinja')
	template_rocket_mixer_config_h = jinja_environment.get_template('rocket_mixer_config_distributed.h.jinja')

	if quantize:
		quantization_offset = np.mean(dataset_training[0])
		quantization_scaling = np.percentile(np.abs(dataset_training[0] - quantization_offset), q=99.9)

		dataset_training[0] = quantize_8_bit(dataset_training[0], quantization_offset, quantization_scaling)
		dataset_evaluation[0] = quantize_8_bit(dataset_evaluation[0], quantization_offset, quantization_scaling)

	num_kernels_per_device, kernel_idx = split_kernels(num_nodes, len(kernels))

	devices_num_features = np.array([len(dilations) * num_biases_per_kernel * n for n in num_kernels_per_device])

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
		'devices_num_features': generate_matrix_code(devices_num_features, use_float=False),
		'devices_kernels_idx': generate_matrix_code(np.array(kernel_idx), use_float=False),
		'max_features_per_device': max(devices_num_features),
		'num_classes': num_classes,
		'batch_size': 128
	}

	output = template_rocket_config_h.render(template_values)
	with open('c_src/cp_firmware/app/rocket_config.h', 'w') as f:
		f.write(output)

	output = template_rocket_config_c.render(template_values)
	with open('c_src/cp_firmware/app/rocket_config.c', 'w') as f:
		f.write(output)

	"""files = ["rocket_config.h", "rocket_config.c", "conv.h", "linear_classifier.h", "conv.c", "linear_classifier.c"]
	for f in files:
		shutil.copy(f"c_src/{'src' if f[-1] == 'c' else 'include'}/{f}", "c_src/cp_firmware/app/")"""

	mixer_config = generate_rocket_mixer_config(num_devices=num_nodes,
												 num_total_nodes=num_nodes,
												 len_time_series=len(dataset_training[0][0]),
												 quantize=quantize,
												 num_classes=num_classes)

	output = template_rocket_mixer_config_h.render(mixer_config)
	with open('c_src/cp_firmware/app/rocket_mixer_config.h', 'w') as f:
		f.write(output)


def generate_data(len_timeseries, quantize):
	"""data = np.random.randn(50, len_timeseries)
	data[0:50, :] = np.random.randn(50, len_timeseries) * 0.9
	label = np.ones((len(data), ))
	label[0:50] = -1.0"""

	"""table = pd.read_table("/home/alex/Downloads/UCRArchive_2018/FordA/FordA_TRAIN.tsv", header=None)

	labels = np.array(table.iloc[:, 0])
	data = np.array(table.iloc[:, 1:])
	return data, labels"""

	num_data = 1000
	np.random.seed(1)
	data = np.zeros((num_data, len_timeseries))
	label = np.ones((num_data,), dtype=np.int8)
	for i in range(num_data // 2):
		data[i, :] = 1 #np.sin(
			#np.array([j / len_timeseries * 15 * np.pi for j in range(len_timeseries)]) + np.random.randn(1) * np.pi)
		label[i] = 1

	for i in range(num_data // 2, num_data):
		data[i, :] = 0 #np.sin(
			#np.array([j / len_timeseries * 14 * np.pi for j in range(len_timeseries)]) + np.random.randn(1) * np.pi)
		label[i] = 2

	"""data[0:50, :] = np.random.randn(50, len_timeseries) * 0.9
	label = np.ones((len(data),))
	label[0:50] = -1.0"""

	shuffle_vec = np.array([i for i in range(len(data))])
	np.random.shuffle(shuffle_vec)
	data = data[shuffle_vec, :]

	if quantize:
		max_int = 2 ** 7 - 1
		scale = max_int / np.max(np.abs(data))
		data = np.clip(data * scale, a_min=-max_int, a_max=max_int)
		print(np.max(data))

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


def generate_data_ucr(num_trajectories, name_dataset, test, frac=1):
	X_train, y_train = load_ucr_dataset(name_dataset, test)
	num_trajectories = min(num_trajectories, int(round(len(X_train) * frac)))

	return (np.array(X_train[0:num_trajectories], dtype=np.float32),
			np.array(y_train[0:num_trajectories], dtype=np.int64))


def calculate_RAM(dilations, num_biases_per_kernel, kernels, num_classes, multiplier=1, offset=None):
	for num_nodes in range(1, 21, 2):
		num_kernels_per_device, kernel_idx = split_kernels(num_nodes, len(kernels))
		devices_num_features = np.array([len(dilations) * num_biases_per_kernel * n for n in num_kernels_per_device])
		memory = max(devices_num_features) / 1000 * 4 * multiplier * num_classes
		if offset is None:
			print(f"({num_nodes},{memory})")
		else:
			print(f"({num_nodes},{offset[num_nodes] - memory})")


if __name__ == "__main__":
	# len_timeseries =  101
	num_nodes = 20
	quantize = True

	# data, labels = generate_data(len_timeseries, quantize)
	np.random.seed(1)
	data_training, labels_training = generate_data_ucr(num_trajectories=8500, name_dataset="OSULeaf", test=False)
	data_test, labels_test = generate_data_ucr(num_trajectories=242, name_dataset="OSULeaf", test=True)
	# data_test, labels_test = generate_data_ucr(num_trajectories=242, name_dataset="OSULeaf", test=True)

	"""data_training, labels_training = generate_data_ucr(num_trajectories=2200, name_dataset="ElectricDevices", test=False)
	data_test, labels_test = generate_data_ucr(num_trajectories=200, name_dataset="ElectricDevices", test=True)"""

	"""data_training, labels_training = generate_data_ucr(num_trajectories=2200, name_dataset="MelbournePedestrian",
													   test=False)
	data_test, labels_test = generate_data_ucr(num_trajectories=200, name_dataset="MelbournePedestrian", test=True)"""

	"""data_training, labels_training = generate_data_ucr(num_trajectories=2200, name_dataset="CricketX",
													   test=False)
	data_test, labels_test = generate_data_ucr(num_trajectories=200, name_dataset="CricketX", test=True)"""

	"""data_training, labels_training = generate_data_ucr(num_trajectories=10, name_dataset="OSULeaf", test=False)
	data_test, labels_test = generate_data_ucr(num_trajectories=10, name_dataset="OSULeaf", test=True)"""

	"""data_training, labels_training = generate_data_ucr(num_trajectories=8500, name_dataset="FaceAll",
													   test=False, frac=0.8)
	data_test, labels_test = generate_data_ucr(num_trajectories=200, name_dataset="FaceAll", test=True)"""

	len_timeseries = len(data_training[0])

	dilations = generate_dilations(len_timeseries)
	kernels = generate_kernels()

	num_biases_per_kernel = int(10_000 / (len(dilations) * len(kernels)))

	num_features = len(dilations) * len(kernels) * num_biases_per_kernel

	num_classes = int(round(max(labels_training)))

	calculate_RAM(dilations, num_biases_per_kernel, kernels, num_classes, multiplier=1)

	print("----------")

	calculate_RAM(dilations, num_biases_per_kernel, kernels, num_classes, multiplier=3)  # ADAM + d_weight

	print("-------------")

	offsets = {1: 0, 3: 0, 5: 244.8, 6: 204.1, 7: 177.1, 8: 163.6, 9: 150.1, 10: 136.7, 11: 123.2, 12: 109.7, 13: 109.8, 14: 96.4, 15: 96.5,
			   16: 96.6, 17: 83.2, 18: 83.3, 19: 83.4, 20: 83.5}  # ElectricDevices

	#offsets = {1: 0, 3: 0, 5: 209.1, 7: 151.4, 9: 128.5, 11: 105.6, 13: 94.3,
	#		   15: 83.0, 17: 71.6, 19: 71.9}  # OSULeaf

	#offsets = {1: 0, 3: 0, 5: 209.1, 7: 241.2, 9: 202.7, 11: 164.2, 13: 145.1,
			   #15: 126.0, 17: 106.9, 19: 107.1}  # Melbourne Pedestrian

	offsets = {1: 0, 3: 0, 5: 209.1, 7: 151.4, 9: 233.8, 11: 189.5, 13: 167.5,
			   15: 145.5, 17: 123.5, 19: 123.7}  # CricketX

	offsets = {1: 0, 3: 0, 5: 209.1, 7: 151.4, 9: 248.3, 11: 200.1, 13: 176.1,
			   15: 152.1, 17: 128.0, 19: 128.3}  # FaceAll

	calculate_RAM(dilations, num_biases_per_kernel, kernels, num_classes, multiplier=4, offset=offsets)
	print(num_classes)
	print(".......")
	#exit(0)

	generate_code([data_training, labels_training], [data_test, labels_test], kernels, dilations, num_biases_per_kernel,
				  quantiles(len(dilations) * len(kernels) * num_biases_per_kernel),
				  num_nodes=num_nodes,
				  quantize=quantize)

	kernel_bins = generate_kernels()

	print(len(kernel_bins))
	for e in kernel_bins:
		# print(f"{e:09b}")
		print(f"{e}")

	print(generate_matrix_code(np.random.randn(1000), use_float=True))
