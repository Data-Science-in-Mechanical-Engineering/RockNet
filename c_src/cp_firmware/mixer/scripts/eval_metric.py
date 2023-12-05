import argparse
import logging
import math
import os
import random
import re
import sys
from pathlib import Path

import matplotlib
import matplotlib.pyplot as plt
import numpy as np
import PyPDF2
import yaml
from fpdf import FPDF

from matplotlib import cm
from matplotlib.colors import ListedColormap, LinearSegmentedColormap

from MixerLogParser import MixerLogParser

#---------------------------------------------------------------------------------------------------
# "Tableau 20" colors as RGB.

tableau20 = [
	(31, 119, 180), (174, 199, 232), (255, 127, 14), (255, 187, 120),
	(44, 160, 44), (152, 223, 138), (214, 39, 40), (255, 152, 150),
	(148, 103, 189), (197, 176, 213), (140, 86, 75), (196, 156, 148),
	(227, 119, 194), (247, 182, 210), (127, 127, 127), (199, 199, 199),
	(188, 189, 34), (219, 219, 141), (23, 190, 207), (158, 218, 229)]

# Scale the RGB values to the [0, 1] range (matplotlib format).
for i in range(len(tableau20)):
	r, g, b = tableau20[i]
	tableau20[i] = (r / 255., g / 255., b / 255.)

#---------------------------------------------------------------------------------------------------
# custom color map

def get_color_map(steps):
	old_cmap = cm.get_cmap('inferno', steps + 1)
	newcolors = old_cmap(np.linspace(0, 1, steps + 1))
	# old_cmap = cm.get_cmap('inferno', 25600)
	# newcolors = old_cmap(np.linspace(0, 1, 25600))
	white = np.array([0, 0, 0, 0])
	newcolors[-1] = white
	my_cmap = ListedColormap(newcolors)

	return my_cmap

#---------------------------------------------------------------------------------------------------
# logging format

fmt	 = '%(asctime)s %(filename)-15.15s:%(lineno)-5d %(levelname)-8s %(message)s'
dfmt = '%H:%M:%S'
logging.basicConfig(format=fmt, datefmt=dfmt)
logger = logging.getLogger('evaluation')

#---------------------------------------------------------------------------------------------------

def extract_infos(file, cfg, pattern):
	results = {}

	with open(file, 'r', encoding='utf-8') as log:
		lines		= log.readlines()
		cur_rnd		= None
		last_nodeid	= None

		for line in lines:
			try:
				nodeid = int(line.split('|')[1].strip())
				if nodeid != last_nodeid:
					last_nodeid = nodeid
					cur_rnd		= None

				if "starting round" in line:
					cur_rnd = int(line.split('starting round')[1].split()[0])
					# logging.debug(f'Found starting round {cur_rnd}')
					continue

				if "preparing round" in line:
					cur_rnd = int(line.split('preparing round')[1].split()[0])
					# logging.debug(f'Found starting round {cur_rnd}')
					continue

				if cur_rnd == None:
					# logging.debug(f'line without prior round information ... skipping line {repr(line)}')
					continue

				# At this point we have node "nodeid" which actually started a round.
				if not nodeid in results:
					results[nodeid] = {}
				if not cur_rnd in results[nodeid]:
					results[nodeid][cur_rnd] = {}

				res = re.search(pattern, line)
				if res:
					data = int(res.group('metric'))
					results[nodeid][cur_rnd]['metric'] = data
					continue

			except ValueError as ve:
				# logging.info(f'ValueError {ve}. Skipping line {repr(line)}')
				logger.info(f'ValueError {ve}. Skipping line {repr(line)}')
				continue

	return results

#---------------------------------------------------------------------------------------------------

def main():
	parser = argparse.ArgumentParser()
	parser.add_argument("path", help="path to log directory")
	parser.add_argument("pattern", help="pattern of metric to evaluate")
	parser.add_argument("--lvl", help="specifies log level", choices=['INFO', 'DEBUG'])
	args = parser.parse_args()

	if not args.lvl:
		logger.setLevel(logging.INFO)
	elif args.lvl == 'INFO':
		logger.setLevel(logging.INFO)
	elif args.lvl == 'DEBUG':
		logger.setLevel(logging.DEBUG)
	else:
		logging.critical('Unknown log level')
		sys.exit()


	### parse

	mlp = MixerLogParser(Path(args.path))
	results = extract_infos(mlp.log_formatted, mlp.exp_config, args.pattern)

	# print information about rounds
	min_rounds = min([(len(rnds), node) for node, rnds in results.items()])
	logger.info(f'Min rounds ({min_rounds[0]}) completed by node {min_rounds[1]}')
	max_rounds = max([(len(rnds), node) for node, rnds in results.items()])
	logger.info(f'Max rounds ({max_rounds[0]}) completed by node {max_rounds[1]}')
	common_rounds = []
	for rnds in results.values():
		if len(common_rounds) == 0:
			common_rounds = list(rnds)
		else:
			common_rounds = [item for item in rnds if item in common_rounds]
	logger.info(f'{len(common_rounds)} rounds completed by all nodes')


	### plot

	data_per_node_all_rounds = []

	for node in sorted(results.keys()):
		rnds = results[node]
		data_one_node_all_rounds = []
		for rnd, metrics in rnds.items():
			try:
				data_one_node_all_rounds.append(metrics['metric'])
			except KeyError as ke:
				logger.debug(f'Missing information {ke} for node {node} in round {rnd}')

		if len(data_one_node_all_rounds) == 0:
			logger.info(f'Couldn\'t find information about the metric for node {node}.')
			return None

		data_per_node_all_rounds.append(data_one_node_all_rounds)

	# plt.subplots(1, 1, figsize=(0.8 * mlp.exp_config['MX_NUM_NODES'], 5))
	plt.figure(figsize=(0.8 * mlp.exp_config['MX_NUM_NODES'], 5))
	plt.violinplot(data_per_node_all_rounds, showmeans=True, showmedians=False, showextrema=False)

	percs = []
	for n in data_per_node_all_rounds:
		p = np.percentile(n, [5, 95])
		percs.append(p)

	flat_data = [item for sublist in data_per_node_all_rounds for item in sublist]
	print(f'mean={round(np.mean(flat_data), 2)} median={round(np.median(flat_data), 2)} 1st={round(np.percentile(flat_data, 1), 2)} 99th={round(np.percentile(flat_data, 99), 2)}')

	for i, p in enumerate(percs, 1):
		plt.hlines(p[0], xmin=i-0.1, xmax=i+0.1)
		plt.hlines(p[1], xmin=i-0.1, xmax=i+0.1)

	plt.xticks(ticks=range(1, mlp.exp_config['MX_NUM_NODES'] + 1), labels=sorted(results.keys()))
	plt.xlabel('Logical Node ID')
	plt.ylabel('Metric')

	plt.show()
	# plt.gcf().savefig('/tmp/metric.pdf', bbox_inches='tight')
	plt.close()

#---------------------------------------------------------------------------------------------------

if __name__ == "__main__":
	main()
