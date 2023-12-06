import serial
import numpy as np
import pandas as pd

import matplotlib.pyplot as plt

if __name__ == "__main__":
	num_nodes = 5

	data = pd.read_csv(f"../Accuracy{num_nodes}.csv")

	plt.plot(data["timestamp"], data["accuracy"])

	plt.xlabel("Time (s)")
	plt.ylabel("Accuracy (%)")

	plt.show()