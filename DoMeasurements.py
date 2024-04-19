import serial
import numpy as np
import pandas as pd

import time


def get_boxplot(a):
	return np.mean(a), np.quantile(a, q=0.25), np.quantile(a, q=0.75), np.quantile(a, q=0.99), np.quantile(a, q=0.01)


if __name__ == "__main__":
	max_num_samples = 1000
	num_nodes = 5
	quantize = True
	name = "Parameterless"
	ser = serial.Serial('COM5', baudrate=921600)
	print("Connected.")

	data = {"timestamp": [], "accuracy": []}

	inference_durations = []
	communication_durations = []
	messages_received = []
	i = 0
	start = 0
	while len(data["accuracy"]) < max_num_samples:
		line = str(ser.readline(), encoding='utf-8')

		if "Accuracy:" in line:
			line.replace("\n", "")
			acc = line.split(":")[-1]
			data["accuracy"].append(int(acc))

			if len(data["timestamp"]) == 0:
				start = time.time()

			data["timestamp"].append(time.time() - start)
			print(f"{data['timestamp'][-1]}: {data['accuracy'][-1]}")

			raw_data = pd.DataFrame(data)

			raw_data.to_csv(f"../Accuracy{name}{num_nodes}{quantize}.csv")

		# print(len(inference_durations))
