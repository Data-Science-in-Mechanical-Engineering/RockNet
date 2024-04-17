import serial
import numpy as np
import pandas as pd

import matplotlib.pyplot as plt


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


if __name__ == "__main__":
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