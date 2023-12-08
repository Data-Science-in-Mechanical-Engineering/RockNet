import serial
import numpy as np
import pandas as pd

import matplotlib.pyplot as plt

if __name__ == "__main__":
	quantize = True
	for num_nodes in [5, 1]:

		data = pd.read_csv(f"../Accuracy{num_nodes}{quantize}.csv")
		print(data["timestamp"])

		plt.plot(data["timestamp"], data["accuracy"], label=f"{num_nodes} device{'s' if num_nodes > 1 else ''}")
		#plt.plot(data["accuracy"], label=f"{num_nodes}")

	plt.xlabel("Time (s)")
	plt.ylabel("Accuracy (%)")
	plt.legend()

	plt.show()