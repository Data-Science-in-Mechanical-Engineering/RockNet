import serial
import numpy as np
import pandas as pd

import matplotlib.pyplot as plt

if __name__ == "__main__":
	for num_nodes in [5, 1]:

		data = pd.read_csv(f"../Accuracy{num_nodes}.csv")
		print(data["timestamp"])

		plt.plot(data["timestamp"], data["accuracy"], label=f"{num_nodes}")
		#plt.plot(data["accuracy"], label=f"{num_nodes}")

	plt.xlabel("Time (s)")
	plt.ylabel("Accuracy (%)")
	plt.legend()

	plt.show()