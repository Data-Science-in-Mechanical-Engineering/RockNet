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

def extract_infos(file, cfg):
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

				if "rank_up_slot" in line:
					# slots is a list of slots when the node's rank increased
					slots = line.split('rank_up_slot=')[1].strip(' [];\n')
					if len(slots) == 0:
						continue
					else:
						slots = [int(s) for s in slots.split(';')]

					# ext_slots is a list with MX_ROUND_LENGTH slots and those slots where the node's rank
					# increased are filled with the actual rank of the node while the others are 0.
					# ext_slots[0] is the 0th slot which is the round start before the first slot.
					# ext_slots is larger than MX_ROUND_LENGTH to handle cases where the nodes reaches full
					# rank at the end of a round.
					rank = 0
					ext_slots = [0] * (cfg['MX_ROUND_LENGTH'] + 5)
					# ext_slots = [0] * (cfg['MX_ROUND_LENGTH'] + 1)
					for slot in slots:
						rank += 1
						# try:
						ext_slots[slot] = rank
						# except IndexError:
						# 	print(line)
						# 	print(cfg['MX_ROUND_LENGTH'])


					# fill slots between rank increases with the actual rank of the node
					slot_full_rank = 0
					last_rank = 0
					for i, s in enumerate(ext_slots):
						# determine in which slot full rank was reached
						if s == cfg['MX_GENERATION_SIZE']:
							slot_full_rank = i
						if s > last_rank:
							last_rank = s
						elif s < last_rank:
							ext_slots[i] = last_rank

					results[nodeid][cur_rnd]['rank_per_slot']	= ext_slots
					results[nodeid][cur_rnd]['slot_full_rank']	= slot_full_rank
					results[nodeid][cur_rnd]['final_rank']		= last_rank
					results[nodeid][cur_rnd]['rank_up_slot']	= slots
					continue

				# discovery information when tracing is activated
				# NOTE: compatibility for older logs
				res = re.search(r'discovery exit slot: (?P<discoveryExit>\d+) \(density: (?P<discoveryDensity>\d+), wake up: (?P<wakeUp>\d+)\)', line)
				if res:
					discoveryExit		= int(res.group('discoveryExit'))
					discoveryDensity	= int(res.group('discoveryDensity'))
					wakeUp				= int(res.group('wakeUp'))
					results[nodeid][cur_rnd]['discoveryExit'] = discoveryExit
					results[nodeid][cur_rnd]['discoveryDensity'] = discoveryDensity
					results[nodeid][cur_rnd]['wakeUp'] = wakeUp
					continue

				# NOTE: compatibility for older logs
				res = re.search(r'rank=(?P<rank>\d+) dec=(?P<decoded>\d+) notDec=(?P<notDecoded>\d+) weak=(?P<weak>\d+) wrong=(?P<wrong>\d+)', line)
				if res:
					# we already retrieve the rank from rank_up_slot list
					# rank				= int(res.group('rank'))
					decoded 			= int(res.group('decoded'))
					notDecoded 			= int(res.group('notDecoded'))
					weak 				= int(res.group('weak'))
					wrong 				= int(res.group('wrong'))

					results[nodeid][cur_rnd]['decoded'] = decoded + weak
					continue

				# NOTE: compatibility for older logs
				res = re.search(r'rank=(?P<rank>\d+) decoded=(?P<decoded>\d+) discovery_exit=(?P<discoveryExit>\d+) discovery_density=(?P<discoveryDensity>\d+)', line)
				if res:
					# we already retrieve the rank from rank_up_slot list
					# rank				= int(res.group('rank'))
					decoded 			= int(res.group('decoded'))
					discoveryExit		= int(res.group('discoveryExit'))
					discoveryDensity	= int(res.group('discoveryDensity'))

					results[nodeid][cur_rnd]['decoded']				= decoded
					results[nodeid][cur_rnd]['discoveryExit']		= discoveryExit
					results[nodeid][cur_rnd]['discoveryDensity']	= discoveryDensity
					continue

				# NOTE: compatibility for older logs
				res = re.search(r'rank=(?P<rank>\d+) decoded=(?P<decoded>\d+)', line)
				if res:
					# we already retrieve the rank from rank_up_slot list
					# rank	= int(res.group('rank'))
					decoded = int(res.group('decoded'))

					results[nodeid][cur_rnd]['decoded'] = decoded
					continue

				res = re.search(r'decoded=(?P<decoded>\d+)\n', line)
				if res:
					decoded = int(res.group('decoded'))

					results[nodeid][cur_rnd]['decoded'] = decoded
					continue

				res = re.search(r'discovery_density: (?P<discoveryDensity>\d+)\n', line)
				if res:
					discoveryDensity = int(res.group('discoveryDensity'))

					results[nodeid][cur_rnd]['discoveryDensity'] = discoveryDensity
					continue

				res = re.search(r'discovery_exit_slot: (?P<discoveryExit>\d+)\n', line)
				if res:
					discoveryExit = int(res.group('discoveryExit'))

					results[nodeid][cur_rnd]['discoveryExit'] = discoveryExit
					continue

			except ValueError as ve:
				# logging.info(f'ValueError {ve}. Skipping line {repr(line)}')
				logger.info(f'ValueError {ve}. Skipping line {repr(line)}')
				continue

	return results

#---------------------------------------------------------------------------------------------------

def node_discoveryNeighbors_violin(mlp, results, force=False):
	outputfile = mlp.plotPath / 'node_discoveryNeighbors_violin.pdf'
	if outputfile.exists() and not force:
		# logging.info(f'{outputfile} already exists. Skipping plot...')
		logger.info(f'{outputfile} already exists. Skipping plot...')
		return outputfile

	num_rounds = min([len(rnds) for rnds in results.values()])
	neighbors_per_node_all_rounds = []

	for node in sorted(results.keys()):
		rnds = results[node]
		neighbors_one_node_all_rounds = []
		for rnd, metrics in rnds.items():
			try:
				neighbors_one_node_all_rounds.append(metrics['discoveryDensity'])
			except KeyError as ke:
				# logging.debug(f'Missing information {ke} for node {node} in round {rnd}')
				logger.debug(f'Missing information {ke} for node {node} in round {rnd}')

		if len(neighbors_one_node_all_rounds) == 0:
			# logging.info(f'Couldn\'t find information about "discoveryDensity" for node {node}.')
			logger.info(f'Couldn\'t find information about "discoveryDensity" for node {node}.')
			return None

		neighbors_per_node_all_rounds.append(neighbors_one_node_all_rounds)

	# plt.subplots(1, 1, figsize=(0.8 * mlp.exp_config['MX_NUM_NODES'], 5))
	plt.figure(figsize=(0.8 * mlp.exp_config['MX_NUM_NODES'], 5))
	plt.violinplot(neighbors_per_node_all_rounds, showmeans=True, showmedians=False, showextrema=False)

	percs = []
	for n in neighbors_per_node_all_rounds:
		p = np.percentile(n, [5, 95])
		percs.append(p)

	for i, p in enumerate(percs, 1):
		plt.hlines(p[0], xmin=i-0.1, xmax=i+0.1)
		plt.hlines(p[1], xmin=i-0.1, xmax=i+0.1)

	plt.xticks(ticks=range(1, mlp.exp_config['MX_NUM_NODES'] + 1), labels=sorted(results.keys()))
	plt.xlabel('Logical Node ID')
	plt.ylabel('Neighbors After Discovery')
	plt.title(f'{mlp.exp_config["MX_PHY_NAME"]}, number of neighbors after discovery phase over {num_rounds} rounds\n({mlp.basepath.name})')

	plt.gcf().savefig(outputfile, bbox_inches='tight')
	plt.close()
	return outputfile

#---------------------------------------------------------------------------------------------------

def slots_node_rank_heatmap_func(mlp, results, func, funcName, force=False):
	outputfile = mlp.plotPath / f'slots_node_rank_heatmap_{funcName}.pdf'
	if outputfile.exists() and not force:
		# logging.info(f'{outputfile} already exists. Delete the file to redo the plot.')
		logger.info(f'{outputfile} already exists. Delete the file to redo the plot.')
		return outputfile

	# rounds completed by all nodes
	num_rounds = min([len(rnds) for rnds in results.values()])

	# applies func to the node's ranks per slot
	data = []
	for nodeid in sorted(results.keys()):
		rank_per_slot = []
		# Groups the same slots across all rounds for every node.
		for slot in zip(*[rnd['rank_per_slot'] for rnd in results[nodeid].values() if 'rank_per_slot' in rnd]):
			rank_per_slot.append(func(slot))
		data.append(rank_per_slot)

	plt.figure(figsize=(15, 0.3 * mlp.exp_config['MX_NUM_NODES']))
	pos = plt.imshow(data, interpolation='none', aspect='auto', cmap='inferno', vmin=0, vmax=mlp.exp_config['MX_GENERATION_SIZE'])
	# pos = plt.imshow(data, interpolation='none', aspect='auto',
	# 				 cmap=get_color_map(mlp.exp_config['MX_GENERATION_SIZE']),
	# 				 vmin=0, vmax=mlp.exp_config['MX_GENERATION_SIZE'])
	plt.colorbar(pos, pad=0.01)

	plt.yticks(ticks=np.arange(len(results.keys())), labels=sorted(results.keys()))
	plt.ylim(len(results.keys()) - 0.5, -0.5)
	plt.xlabel('slots')
	plt.ylabel('nodes')
	plt.title(f'{mlp.exp_config["MX_PHY_NAME"]}, {funcName} ranks per slot over {num_rounds} rounds\n({mlp.basepath.name})')

	plt.tight_layout()
	plt.gcf().savefig(outputfile, bbox_inches='tight')
	plt.close()
	return outputfile

#---------------------------------------------------------------------------------------------------

def slots_node_rank_heatmap_rounds(mlp, results, rounds, force=False):
	outputfile = mlp.plotPath / f'slots_node_rank_heatmap_rounds_{rounds[0]}_{rounds[1]}.pdf'
	if outputfile.exists() and not force:
		# logging.info(f'{outputfile} already exists. Delete the file to redo the plot.')
		logger.info(f'{outputfile} already exists. Delete the file to redo the plot.')
		return outputfile

	# rounds completed by all nodes
	rnd_intersection = []
	for rnds in results.values():
		if len(rnd_intersection) == 0:
			rnd_intersection = list(rnds)
		else:
			rnd_intersection = [item for item in rnds if item in rnd_intersection]

	# TODO: It could be that a incomplete round is in rnd_intersection, so we workaround by cutting off the last round.
	rnd_intersection = rnd_intersection[:-1]

	num_rounds = len(rnd_intersection)
	# round_selection = random.sample(rnd_intersection, k=min(num_rounds, rounds))
	round_selection = rnd_intersection[rounds[0]:rounds[1]]
	# logging.info(f'Plotting {len(round_selection)} rounds: {round_selection}')
	logger.info(f'Plotting {len(round_selection)} rounds: {round_selection}')

	# rounds_to_plot = min(num_rounds, rounds)
	rounds_to_plot = len(round_selection)
	fig, axarr = plt.subplots(rounds_to_plot, 1, figsize=(10, rounds_to_plot * mlp.exp_config['MX_NUM_NODES'] * 0.15))

	if num_rounds == 1:
		rnd_axs = [(round_selection[0], axarr)]
	else:
		rnd_axs = zip(round_selection, axarr)

	for rnd, ax in rnd_axs:
		data = []
		for nodeid in sorted(results.keys()):
			data.append(results[nodeid][rnd]['rank_per_slot'])

		pos = ax.imshow(data, interpolation='none', aspect='auto', cmap='inferno',
						vmin=0, vmax=mlp.exp_config['MX_GENERATION_SIZE'])
		fig.colorbar(pos, ax=ax, pad=0.01)

		ax.set_yticks(np.arange(len(results.keys())))
		ax.set_yticklabels(sorted(results.keys()))
		ax.set_ylim(len(results.keys()) - 0.5, -0.5)

		ax.set_title(f'{mlp.exp_config["MX_PHY_NAME"]}, Round {rnd}\n({mlp.basepath.name})')

	plt.tight_layout()
	plt.gcf().savefig(outputfile, bbox_inches='tight')
	plt.close()
	return outputfile

#---------------------------------------------------------------------------------------------------

def slots_rank_linePerNode_func(mlp, results, func, funcName, force=False):
	outputfile = mlp.plotPath / f'slots_rank_linePerNode_{funcName}.pdf'
	if outputfile.exists() and not force:
		# logging.info(f'{outputfile} already exists. Delete the file to redo the plot.')
		logger.info(f'{outputfile} already exists. Delete the file to redo the plot.')
		return outputfile

	# rounds completed by all nodes
	num_rounds = min([len(rnds) for rnds in results.values()])

	nodes_per_row = 7
	cols = min(mlp.exp_config['MX_NUM_NODES'], nodes_per_row)
	rows = math.ceil(mlp.exp_config['MX_NUM_NODES'] / nodes_per_row)
	fig, axarr = plt.subplots(rows, cols, sharex=True, sharey=True, figsize=(cols * 2, rows * 2))

	# flatten axarr
	if isinstance(axarr[0], np.ndarray):
		axarr = [item for sublist in axarr for item in sublist]

	data = {}
	for nodeid in sorted(results.keys()):
		rank_per_slot = []
		# Groups the same slots across all rounds for every node.
		for slot in zip(*[rnd['rank_per_slot'] for rnd in results[nodeid].values() if 'rank_per_slot' in rnd]):
			rank_per_slot.append(func(slot))
		data[nodeid] = rank_per_slot

	# This loop iterates only len(results.keys()) often even if axarr is bigger.
	for nodeid, ax in zip(sorted(results.keys()), axarr):
		ax.set_xlabel('slots')
		ax.set_ylabel('rank')
		ax.set_title(f'node {nodeid}')
		# ax.text(0.05, 0.9, f'node {nodeid}', transform=ax.transAxes)
		ax.set_ylim(0, mlp.exp_config['MX_GENERATION_SIZE'])
		y = data[nodeid]
		x = range(len(y))
		ax.plot(x, y, '-k')

	# common title for all subplots
	plt.suptitle(f'{mlp.exp_config["MX_PHY_NAME"]}, {funcName} rank per slot over {num_rounds} rounds\n({mlp.basepath.name})', x=0.5, y=1.03)
	plt.tight_layout()
	plt.gcf().savefig(outputfile, bbox_inches='tight')
	plt.close()
	return outputfile

#---------------------------------------------------------------------------------------------------

def node_fullRankSlot_reliability_violin(mlp, results, force=False):
	outputfile = mlp.plotPath / 'node_fullRankSlot_reliability_violin.pdf'
	if outputfile.exists() and not force:
		# logging.info(f'{outputfile} already exists. Skipping plot...')
		logger.info(f'{outputfile} already exists. Skipping plot...')
		return outputfile

	num_rounds = min([len(rnds) for rnds in results.values()])
	full_rank_per_node_all_rounds = []
	data_decoded_per_node_all_rounds = []

	# {nodeid: {round: {slots, ...}}}
	last_num_rounds = None
	for node in sorted(results.keys()):
		rnds = results[node]

		if last_num_rounds == None:
			last_num_rounds = len(rnds.keys())
		elif last_num_rounds != len(rnds.keys()):
			# logging.debug(f'Inconsistency in number of rounds. Node {node} has {len(rnds.keys())} rounds compared to {last_num_rounds} rounds of previous nodes.')
			logger.debug(f'Inconsistency in number of rounds. Node {node} has {len(rnds.keys())} rounds compared to {last_num_rounds} rounds of previous nodes.')

		full_rank_one_node_all_rounds = []
		data_decoded_one_node_all_rounds = []
		# for metrics in rnds.values():
		for rnd, metrics in rnds.items():
			try:
				# Not reaching full rank will not affect the full rank distribution plot but reliability.
				if metrics['slot_full_rank'] != 0:
					full_rank_one_node_all_rounds.append(metrics['slot_full_rank'])
				data_decoded_one_node_all_rounds.append(metrics['decoded'])
			except KeyError as ke:
				# logging.debug(f'Missing information for node {node} in round {rnd}: {ke}')
				logger.debug(f'Missing information for node {node} in round {rnd}: {ke}')

		if len(full_rank_one_node_all_rounds) == 0:
			# logging.error(f'Couldn\'t find information about "slot_full_rank" for node {node}. Skipping plot!')
			logger.error(f'Couldn\'t find information about "slot_full_rank" for node {node}. Skipping plot!')
			return
		if len(data_decoded_one_node_all_rounds) == 0:
			# logging.error(f'Couldn\'t find information about "decoded" for node {node}. Skipping plot!')
			logger.error(f'Couldn\'t find information about "decoded" for node {node}. Skipping plot!')
			return

		full_rank_per_node_all_rounds.append(full_rank_one_node_all_rounds)
		data_decoded_per_node_all_rounds.append(data_decoded_one_node_all_rounds)

	reliability = [round(sum(node) / (len(node) * mlp.exp_config['MX_GENERATION_SIZE']) * 100, 1) for node in data_decoded_per_node_all_rounds]

	# plt.subplots(1, 1, figsize=(0.8 * mlp.exp_config['MX_NUM_NODES'], 5))
	plt.figure(figsize=(0.8 * mlp.exp_config['MX_NUM_NODES'], 5))
	plt.violinplot(full_rank_per_node_all_rounds, showmeans=True, showmedians=False, showextrema=False)

	percs = []
	for n in full_rank_per_node_all_rounds:
		p = np.percentile(n, [5, 95])#, axis=1)
		percs.append(p)

	for i, p in enumerate(percs, 1):
		plt.hlines(p[0], xmin=i-0.1, xmax=i+0.1)
		plt.hlines(p[1], xmin=i-0.1, xmax=i+0.1)

	bot,top = plt.ylim()
	plt.ylim([bot - 24, top])
	plt.xticks(ticks=range(1, mlp.exp_config['MX_NUM_NODES'] + 1), labels=sorted(results.keys()))

	for i, v in enumerate(reliability, 1):
		plt.text(i, bot - 12, f'{v}%', horizontalalignment='center')

	plt.xlabel('Logical Node ID')
	plt.ylabel('Full Rank Slot')
	plt.title(f'{mlp.exp_config["MX_PHY_NAME"]}, time needed for full rank over {num_rounds} rounds\n({mlp.basepath.name})')
	# plt.legend(labels=[str(i) for i in range(1,21)], bbox_to_anchor=(1.05, 1))
	# plt.show()
	plt.gcf().savefig(outputfile, bbox_inches='tight')
	plt.close()
	return outputfile

#---------------------------------------------------------------------------------------------------

def create_config_pdf(mlp):
	outputfile = mlp.plotPath / 'config.pdf'

	pdf = FPDF(format=(400,125))
	pdf.add_page()
	pdf.set_font('Courier', '', 12)
	key_width = 25

	for k,v in mlp.exp_config.items():
		# NODE_MAPPING usually spans multiple lines and needs to be split into chunks
		if k == 'NODE_MAPPING':
			nodemap = list(v)
			for i in range(0, len(nodemap), 10):
				# s = str(nodemap[i:i+10]).strip('[] ')
				s = ""
				for node in nodemap[i:i+10]:
					s += f'{str(node):<10},'
				if i == 0:
					pdf.cell(0, 5, f'{k:<{key_width}}: {s}', ln=1)
				else:
					pdf.cell(0, 5, f'{"":<{key_width}}  {s}', ln=1)
		else:
			pdf.cell(0, 5, f'{k:<{key_width}}: {v}', ln=1)

	pdf.output(outputfile, 'F')
	return outputfile

#---------------------------------------------------------------------------------------------------

def create_overview(mlp, plotFiles):
	pdfMerger = PyPDF2.PdfFileMerger()
	for pdf in plotFiles:
		pdfMerger.append(PyPDF2.PdfFileReader(str(pdf)))

	with open(mlp.plotPath / 'overview.pdf', 'wb') as f:
		pdfMerger.write(f)

#---------------------------------------------------------------------------------------------------

def create_experiment_plots(path, force=False):
	mlp = MixerLogParser(path)
	results = extract_infos(mlp.log_formatted, mlp.exp_config)

	# print information about rounds
	min_rounds = min([(len(rnds), node) for node, rnds in results.items()])
	# logging.info(f'Min rounds ({min_rounds[0]}) completed by node {min_rounds[1]}')
	logger.info(f'Min rounds ({min_rounds[0]}) completed by node {min_rounds[1]}')
	max_rounds = max([(len(rnds), node) for node, rnds in results.items()])
	# logging.info(f'Max rounds ({max_rounds[0]}) completed by node {max_rounds[1]}')
	logger.info(f'Max rounds ({max_rounds[0]}) completed by node {max_rounds[1]}')
	common_rounds = []
	for rnds in results.values():
		if len(common_rounds) == 0:
			common_rounds = list(rnds)
		else:
			common_rounds = [item for item in rnds if item in common_rounds]
	# logging.info(f'{len(common_rounds)} rounds completed by all nodes')
	logger.info(f'{len(common_rounds)} rounds completed by all nodes')

	plotFiles = []

	p = create_config_pdf(mlp)
	if p and p.exists():
		plotFiles.append(p)

	p = slots_node_rank_heatmap_func(mlp, results, lambda x: np.mean(x), 'mean', force)
	if p and p.exists():
		plotFiles.append(p)

	p = slots_node_rank_heatmap_func(mlp, results, lambda x: min(x), 'min', force)
	if p and p.exists():
		plotFiles.append(p)

	p = slots_node_rank_heatmap_func(mlp, results, lambda x: max(x), 'max', force)
	if p and p.exists():
		plotFiles.append(p)

	p = node_fullRankSlot_reliability_violin(mlp, results, force)
	if p and p.exists():
		plotFiles.append(p)

	p = slots_rank_linePerNode_func(mlp, results, lambda x: np.mean(x), 'mean', force)
	if p and p.exists():
			plotFiles.append(p)

	p = node_discoveryNeighbors_violin(mlp, results, force)
	if p and p.exists():
			plotFiles.append(p)

	# exclude rounds plot from overview
	# slots_node_rank_heatmap_rounds(mlp, results, (0,19), force)
	# slots_node_rank_heatmap_rounds(mlp, results, (105,119), force)

	create_overview(mlp, plotFiles)

#---------------------------------------------------------------------------------------------------

def main():
	parser = argparse.ArgumentParser()
	parser.add_argument("path", help="path to log directory")
	parser.add_argument("--lvl", help="specifies log level", choices=['INFO', 'DEBUG'])
	parser.add_argument("--all", help="path contains multiple experiments that should be all evaluated",
						action='store_true')
	parser.add_argument("--force", help="force plotting even if the plot already exists",
						action='store_true')
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

	if args.all:
		for path in Path(args.path).iterdir():
			create_experiment_plots(path, args.force)
	else:
		create_experiment_plots(Path(args.path), args.force)

#---------------------------------------------------------------------------------------------------

if __name__ == "__main__":
	main()
