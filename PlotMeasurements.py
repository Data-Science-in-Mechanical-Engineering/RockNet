import numpy as np
import pandas as pd

import matplotlib.pyplot as plt


voltage = 3
power_tx_rampup = voltage * 13e-3
power_rx_rampup = voltage * 13e-3
power_rx_air = voltage * 6.4e-3
power_tx_air = voltage * 13.63e-3  #6.6e-3
power_calculation = voltage * 3.71e-3
power_low_power = voltage * 205e-6
power_timeout = voltage * 6e-3


def plot_ram():
	quantize = True
	print(plt.style.available)
	plt.figure(figsize=(3, 3))
	plt.tight_layout()
	plt.style.use('seaborn-talk')

	plt.plot([1, 3, 5, 7, 9, 11, 13, 15], [235.8, 83.7, 53.9, 40.5, 35.2, 29.9, 27.4, 24.8])

	plt.xlim(0, 16)
	plt.ylim(0, 256)

	plt.xlabel("Number devices")
	plt.ylabel("RAM usage (kB)")
	plt.savefig('C:\\Users\\mf724021\\Downloads\\RAMUsage.png', bbox_inches='tight')
	plt.show()


def parse_csv(name, num_nodes):
	data = pd.read_csv(f"../Accuracy{name}{num_nodes}{True}.csv")
	data.loc[:, "timestamp"] = data["timestamp"] / 3600
	data.loc[:, "accuracy"] = data["accuracy"] / 10
	print(f"{name}, {num_nodes}")
	print(max(data["accuracy"]))
	data.to_csv(f"../AccuracyFinal{name}{num_nodes}{True}.csv")


def get_max_acc(name, num_nodes):
	data = pd.read_csv(f"../Accuracy{name}{num_nodes}{True}.csv")
	data.loc[:, "timestamp"] = data["timestamp"] / 3600
	data.loc[:, "accuracy"] = data["accuracy"] / 10
	max_acc = max(data["accuracy"])
	return data.loc[data["accuracy"] == max_acc, "timestamp"].iloc[0], max_acc


def time_till_acc(name, num_nodes, acc):
	data = pd.read_csv(f"../Accuracy{name}{num_nodes}{True}.csv")
	data.loc[:, "timestamp"] = data["timestamp"] / 3600
	data.loc[:, "accuracy"] = data["accuracy"] / 10

	return data.loc[data["accuracy"]>acc, "timestamp"].iloc[0]

def min_len(*lists):
	return min([len(l) for l in lists])


def energy_till_accuracy(name, num_nodes, accuracy):
	with open(f"../Log{name}{num_nodes}.txt", 'r') as f:
		# Read the contents of the file into a variable
		logs = f.read()

	power_rx = None
	power_tx = None

	radio_rx_times = []
	radio_tx_times = []
	low_power_times = []
	num_rx_timeout = []
	com_time = []

	log_data = {"radio_TX_time": radio_tx_times, "radio_RX_time": radio_rx_times, "low_power_time": low_power_times,
				"num_rx_timeout": num_rx_timeout, "com_time": com_time}

	energy_consumed_communication = []
	energy_consumed_computation = []

	calc_times = []
	start_calculations = False

	for l in logs.split("\n"):
		l = l.replace("us", "")
		data = l.split(":")
		header = data[0]
		if header in log_data:
			log_data[header].append(int(data[1]))

		if header == "Accuracy":
			if accuracy < int(data[1]) / 10:
				break

		if header == "packet_air_time":
			air_time = int(data[1])
			power_rx = (power_rx_rampup * 70 + power_rx_air * (air_time-70)) / (air_time)
			power_tx = (power_tx_rampup * 70 + power_tx_air * (air_time-70)) / (air_time)

		if header == "# ID":
			if start_calculations:
				calc_times.append(0)
				for i in data[1].split():
					calc_times_part = i.split("=")
					if calc_times_part[0] == "finished_cb_time" or calc_times_part[0] == "start_cb_time":
						calc_times[-1] += int(calc_times_part[1])

				energy_consumed_computation.append(0)
				energy_consumed_communication.append(0)

				energy_consumed_computation[-1] = calc_times[-1] * 1e-6 * power_calculation

				energy_consumed_communication[-1] = (radio_rx_times[-1] - num_rx_timeout[-1] * 140) * 1e-6 * power_rx
				energy_consumed_communication[-1] += num_rx_timeout[-1] * 140 * 1e-6 * power_timeout
				energy_consumed_communication[-1] += radio_tx_times[-1] * 1e-6 * power_tx
				energy_consumed_communication[-1] += low_power_times[-1] * 1e-6 * power_low_power

			if power_rx is not None:
				start_calculations = True

	return np.sum(energy_consumed_communication) + np.sum(energy_consumed_computation)

def analyze_logs(name, num_nodes):
	with open(f"../Log{name}{num_nodes}.txt", 'r') as f:
		# Read the contents of the file into a variable
		logs = f.read()

	num_datapoints = 1000

	power_rx = None
	power_tx = None

	radio_rx_times = []
	radio_tx_times = []
	low_power_times = []
	num_rx_timeout = []
	com_time = []

	log_data = {"radio_TX_time": radio_tx_times, "radio_RX_time": radio_rx_times, "low_power_time": low_power_times,
				"num_rx_timeout": num_rx_timeout, "com_time": com_time}

	energy_consumed_communication = []
	energy_consumed_computation = []

	calc_times = []
	start_calculations = False

	for l in logs.split("\n"):
		l = l.replace("us", "")
		data = l.split(":")
		header = data[0]
		if header in log_data:
			log_data[header].append(int(data[1]))

		if header == "packet_air_time":
			air_time = int(data[1])
			power_rx = (power_rx_rampup * 70 + power_rx_air * (air_time-70)) / (air_time)
			power_tx = (power_tx_rampup * 70 + power_tx_air * (air_time-70)) / (air_time)

		if header == "# ID":
			if start_calculations:
				calc_times.append(0)
				for i in data[1].split():
					calc_times_part = i.split("=")
					if calc_times_part[0] == "finished_cb_time" or calc_times_part[0] == "start_cb_time":
						calc_times[-1] += int(calc_times_part[1])

				energy_consumed_computation.append(0)
				energy_consumed_communication.append(0)

				energy_consumed_computation[-1] = calc_times[-1] * 1e-6 * power_calculation

				energy_consumed_communication[-1] = (radio_rx_times[-1] - num_rx_timeout[-1] * 140) * 1e-6 * power_rx
				energy_consumed_communication[-1] += num_rx_timeout[-1] * 140 * 1e-6 * power_timeout
				energy_consumed_communication[-1] += radio_tx_times[-1] * 1e-6 * power_tx
				energy_consumed_communication[-1] += low_power_times[-1] * 1e-6 * power_low_power

			if power_rx is not None:
				start_calculations = True

		if min_len(radio_rx_times, radio_tx_times, low_power_times, calc_times) >= num_datapoints:
			break

	# now do low-power times during computation
	calc_times = np.array(calc_times)
	low_power_calc_times = max(calc_times) - calc_times

	energy_consumed_computation = np.array(energy_consumed_computation) + low_power_calc_times * 1e-6 * power_low_power

	print(num_nodes)
	print(f"RX: {max(radio_rx_times)}")
	print(f"TX: {max(radio_tx_times)}")
	print(f"low-power: {max(low_power_times)}")
	print(f"calc-times: {max(calc_times)}")

	total_energy = np.array(energy_consumed_computation) + np.array(energy_consumed_communication)
	print(f"{min(energy_consumed_communication)}, {max(energy_consumed_communication)}")
	print(f"{min(energy_consumed_computation)}, {max(energy_consumed_computation)}")
	max_idx = np.argmax(total_energy)
	print(total_energy[max_idx])

	middle_energy_consumed_computation = np.mean(energy_consumed_computation)
	middle_energy_consumed_communication = np.mean(energy_consumed_communication)

	return (middle_energy_consumed_computation * 1e3, -(np.percentile(energy_consumed_computation, 1) - middle_energy_consumed_computation) * 1e3, (np.percentile(energy_consumed_computation, 99) - np.median(energy_consumed_computation)) * 1e3,
			middle_energy_consumed_communication * 1e3, -(np.percentile(energy_consumed_communication, q=1) - middle_energy_consumed_communication) * 1e3, (np.percentile(energy_consumed_communication, q=99) - np.median(energy_consumed_communication)) * 1e3,
			max(calc_times) * 1e-3, max(com_time) * 1e-3)


def print_table(data, num_nodes_start, num_nodes_end, error_plus=None, error_minus=None):
	for i, num_nodes in enumerate(range(num_nodes_start, num_nodes_end+1, 2)):
		print(f"({num_nodes},{data[i]})" + ("" if error_plus is None else f"+=(0, {error_plus[i]})") +
			  ("" if error_minus is None else f"-=(0, {error_minus[i]})"))


if __name__ == "__main__":
	name = "FaceAll"  #"OSULeaf"#"ElectricDevices"
	comps = []
	comps_errors_plus = []
	comps_errors_minus = []
	coms = []
	coms_errors_plus = []
	coms_errors_minus = []
	calc_times = []
	com_times = []
	num_nodes_start = 9
	for i in range(num_nodes_start, 20, 2):
		comp, comp_em, comp_ep, com, com_em, com_ep, calc_time, com_time = analyze_logs(name, i)
		comps.append(comp)
		comps_errors_plus.append(comp_ep)
		comps_errors_minus.append(comp_em)
		coms.append(com)
		coms_errors_plus.append(com_ep)
		coms_errors_minus.append(com_em)
		calc_times.append(calc_time)
		com_times.append(com_time)

	print_table(comps, num_nodes_start, 19, error_plus=comps_errors_plus, error_minus=comps_errors_minus)
	print("-------")
	print_table(coms, num_nodes_start, 19, error_plus=coms_errors_plus, error_minus=coms_errors_minus)
	print("-------")
	print_table(calc_times, num_nodes_start, 19)
	print("-------")
	print_table(com_times, num_nodes_start, 19)
	print("-------")

	#analyze_logs("OSULeaf", 20)
	#exit(0)

	print("Latency")
	max_acc_aifes_time, max_acc_aifes = get_max_acc(name + "NN", 1)
	max_acc_rocknet_time, max_acc_rocknet = get_max_acc(name, 20)

	print(f"max AIFES: {max_acc_aifes_time}h: {max_acc_aifes}%")
	print(f"max ROCKNET: {max_acc_rocknet_time}h: {max_acc_rocknet}%")

	print(f"Latency ROCKNET till max aifes: {time_till_acc(name, 20, max_acc_aifes)}")

	print("Energy consumption")
	print(f"Energy AIFES max: {max_acc_aifes_time * 3600*power_calculation}J")
	energy = energy_till_accuracy(name, 20, max_acc_rocknet)
	print(f"Energy ROCKNET max: {energy} J")
	energy = energy_till_accuracy(name, 20, max_acc_aifes)
	print(f"Energy ROCKNET till AIfES max: {energy} J")

	parse_csv("OSULeaf", 20)
	parse_csv("OSULeafNN", 1)

	parse_csv("ElectricDevices", 20)
	parse_csv("ElectricDevicesNN", 1)

	parse_csv("FaceAll", 20)
	parse_csv("FaceAllNN", 1)

	exit(0)
	plot_ram()
	quantize = True
	name = "Parameterless"
	print(plt.style.available)
	plt.figure(figsize=(3, 3))
	plt.tight_layout()
	plt.style.use('seaborn-talk')
	for num_nodes in [5]:

		data = pd.read_csv(f"../Accuracy{name}{num_nodes}{quantize}.csv")
		print(data["timestamp"])

		plt.plot(data["timestamp"], data["accuracy"], label=f"{num_nodes} device{'s' if num_nodes > 1 else ''}")
		#plt.plot(data["accuracy"], label=f"{num_nodes}")

	plt.xlabel("Wall time (s)")
	plt.ylabel("Accuracy (%)")
	plt.legend()
	plt.savefig('C:\\Users\\mf724021\\Downloads\\RocketTraining.png', bbox_inches='tight')
	plt.show()