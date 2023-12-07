import serial
import numpy as np
import pandas as pd

import time


def get_boxplot(a):
	return np.mean(a), np.quantile(a, q=0.25), np.quantile(a, q=0.75), np.quantile(a, q=0.99), np.quantile(a, q=0.01)


if __name__ == "__main__":
	max_num_samples = 1000
	ser = serial.Serial('COM4', baudrate=921600)
	print("Connected.")

	data = {"timestamp": [], "accuracy": []}

	while True:
		line = str(ser.readline(), encoding='utf-8')

		if "m:" in line:
			line.replace("\n", "")
			m = int(line.split(":")[-1])
			if m < 5:
				print(f"Lost message {m}")

		# print(len(inference_durations))
