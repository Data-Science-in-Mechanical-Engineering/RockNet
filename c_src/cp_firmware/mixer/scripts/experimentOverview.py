import argparse
import csv
import logging
import os
import sys
from pathlib import Path

import yaml


def main():
	parser = argparse.ArgumentParser()
	parser.add_argument("path", help="path to log directory")
	parser.add_argument("--lvl", help="specifies log level", choices=['INFO', 'DEBUG'])
	args = parser.parse_args()

	# logging format
	fmt	 = '%(asctime)s %(filename)-15.15s:%(lineno)-5d %(levelname)-8s %(message)s'
	dfmt = '%H:%M:%S'
	if not args.lvl:
		logging.basicConfig(level=logging.INFO, format=fmt, datefmt=dfmt)
	elif args.lvl == 'INFO':
		logging.basicConfig(level=logging.INFO, format=fmt, datefmt=dfmt)
	elif args.lvl == 'DEBUG':
		logging.basicConfig(level=logging.DEBUG, format=fmt, datefmt=dfmt)
	else:
		logging.critical('Unknown log level')
		sys.exit()


	basepath = Path(args.path)
	exp_configs = list(basepath.glob('**/log_config'))
	exp_configs_dirs = [d.parents[1] for d in exp_configs]

	exp_dirs = set()
	for d in basepath.rglob('*'):
		if d.is_dir():
			dirs = [i for i in d.iterdir() if i.is_dir()]
			if len(dirs) == 0:
				# at this point, d is either an experiment that was not yet evaluated or
				# the "generated_logs" / "plots" folders of an evaluated experiment
				if d.name == "generated_logs" or d.name == "plots":
					exp_dirs.add(d.parent)
				else:
					exp_dirs.add(d)

	exps_not_evaluated = exp_dirs.difference(exp_configs_dirs)
	logging.info(f'{len(exps_not_evaluated)} experiments are not evaluated:')
	for e in exps_not_evaluated:
		logging.info(f'\t{e}')

	# If newline='' is not specified, newlines embedded inside quoted fields will not be interpreted correctly,
	# and on platforms that use \r\n linendings on write an extra \r will be added. It should always be safe to
	# specify newline='', since the csv module does its own (universal) newline handling.
	# https://docs.python.org/3.6/library/csv.html#id3
	with open(basepath / 'experiments.txt', 'w', encoding='utf-8', newline='') as out:
		fieldnames = [
			'MX_NUM_NODES',
			'MX_GENERATION_SIZE',
			'MX_PAYLOAD_SIZE',
			'MX_PHY_MODE',
			'MX_PHY_NAME',
			'MX_ROUND_LENGTH',
			'MX_SLOT_LENGTH',
			'MX_SMART_SHUTDOWN_MODE',
			'DESCRIPTION',
			'MX_INITIATOR_ID',
			'MX_AGE_TO_INCLUDE_PROBABILITY',
			'MX_AGE_TO_TX_PROBABILITY',
			'MX_COORDINATED_TX',
			'MX_HISTORY_DISCOVERY_BEHAVIOR',
			'MX_REQUEST',
			'MX_REQUEST_HEURISTIC',
			'MX_SMART_SHUTDOWN',
			'MX_WEAK_ZEROS',
			'MX_VERBOSE_STATISTICS',
			'MAX_PROPAGATION_DELAY',
			'RX_WINDOW_INCREMENT',
			'RX_WINDOW_MIN',
			'RX_WINDOW_MAX',
			'GRID_DRIFT_FILTER_DIV',
			'GRID_TICK_UPDATE_DIV',
			'GRID_DRIFT_MAX',
			'TX_OFFSET_FILTER_DIV',
			'TX_OFFSET_MAX']

		frontAdditionalFields = ['path']
		backAdditionalFields = []

		# writer = csv.writer(out, delimiter=',', quoting=csv.QUOTE_MINIMAL, fieldnames=fieldnames)
		writer = csv.DictWriter(out, delimiter=',', quoting=csv.QUOTE_MINIMAL,
								fieldnames=frontAdditionalFields + fieldnames + backAdditionalFields)
		writer.writeheader()

		for exp in sorted(exp_configs):
			with open(exp, 'r') as f:
				cfg = yaml.load(f, Loader=yaml.Loader)

				# process config fields
				fieldDict = {}
				for field in fieldnames:
					if field in cfg:
						fieldDict[field] = cfg[field]
					else:
						fieldDict[field] = '-'

				# process additional fields
				# fieldDict['path'] = exp.parents[1]
				fieldDict['path'] = "/".join(exp.parts[-5:-2])

				writer.writerow(fieldDict)


if __name__ == "__main__":
	main()
