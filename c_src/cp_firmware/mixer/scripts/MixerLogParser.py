import argparse
import logging
import os
import re
import sys
from datetime import datetime
from pathlib import Path

import yaml


class MixerLogParser():

	def __init__(self, basepath, files=None, description=None, testbed=None):
		logging.info(f'Initializing MixerLogParser for experiment {Path(basepath).name}')

		# directories created by the script
		self.basepath	= Path(basepath)
		self.outputPath	= Path(basepath) / 'generated_logs'
		self.plotPath	= Path(basepath) / 'plots'

		# logs created by the script
		self.log_formatted	= self.outputPath / 'log_formatted'
		self.log_filtered	= self.outputPath / 'log_filtered'
		self.log_config		= self.outputPath / 'log_config'

		# create directories if they don't exist
		if not self.outputPath.exists():
			Path.mkdir(self.outputPath)
		if not self.plotPath.exists():
			Path.mkdir(self.plotPath)

		# format the raw experiment log when the files parameter is given, otherwise the formatted log must already exist
		if files:
			logging.info(f'Found {len(files)} log files.')
			self.files   = files
			self.testbed = testbed
			self._format_log()
		elif not self.log_formatted.exists():
			logging.critical(f'{self.log_formatted} does not exist.')
			sys.exit()

		# extract experiment configuration when the description parameter is given, otherwise configuration must already exist
		if description:
			self.description = description
			self._extract_config()
		elif not self.log_config.exists():
			logging.critical(f'{self.log_config} does not exist.')
			sys.exit()

		# load configuration into a data structure for convinient access
		with open(self.log_config, 'r') as f:
			self.exp_config = yaml.load(f, Loader=yaml.Loader)


	def _format_log(self):
		if self.log_formatted.exists():
			logging.info(f'{self.log_formatted} already exists, skipping this step.')
		else:
			logging.info(f'Creating {self.log_formatted}')

			# TODO: automatically detect testbed

			if not self.testbed:
				logging.critical('Testbed format is not provided')
				sys.exit()

			elif self.testbed == 'local':
				logging.info('Parsing experiment log of local testbed')
				# Gather all lines of each node.
				nodelog = {}
				for f in self.files:
					# potential encodings: utf-8, iso-8859-1, ascii, ...
					with open(f, 'r', encoding='iso-8859-1') as log:
						lines = log.readlines()
						# parse log until node ID is found
						for line in lines:
							if '# ID:' in line:
								nodeid = int(line.split()[1].split(':')[1])
								nodelog[nodeid] = []
								break
						for line in lines:
							nodelog[nodeid].append(line)

				# Rewrite log with a common format and ascending node IDs.
				with open(self.log_formatted, 'w', encoding='utf-8') as out:
					for node in sorted(nodelog.keys()):
						for line in nodelog[node]:
							if '\\x' in repr(line):
								logging.debug(f'Skipping line: {repr(line)}')
								continue
							timestamp = 0
							msg = line
							msg = re.sub(r'# ID:\d+ ', '', msg)
							out.write(f'{timestamp:0<17} | {node:>3} | {msg}')

			elif self.testbed == 'graz':
				logging.info('Parsing experiment log of graz testbed')
				# Gather all lines of each node.
				nodelog = {}
				for f in self.files:
					# potential encodings: utf-8, iso-8859-1, ascii, ...
					with open(f, 'r', encoding='iso-8859-1') as log:
						lines = log.readlines()
						# parse log until node ID is found
						for line in lines:
							if 'starting node' in line:
								nodeid = int(line.split('node')[1].split()[0])
								nodelog[nodeid] = []
								break
						for line in lines:
							nodelog[nodeid].append(line)

				# Rewrite log with a common format and ascending node IDs.
				with open(self.log_formatted, 'w', encoding='utf-8') as out:
					for node in sorted(nodelog.keys()):
						for line in nodelog[node]:
							if '\\x' in repr(line):
								logging.debug(f'Skipping line: {repr(line)}')
								continue

							if sys.version_info >= (3, 7):
								timestamp = datetime.fromisoformat(line.split('|')[0]).timestamp()
							else:
								datestring = line.split('|')[0]
								year = int(datestring.split()[0].split('-')[0])
								month = int(datestring.split()[0].split('-')[1])
								day = int(datestring.split()[0].split('-')[2])
								hour = int(datestring.split()[1].split(':')[0])
								minute = int(datestring.split()[1].split(':')[1])
								second = int(datestring.split()[1].split(':')[2].split('.')[0])
								microsecond = int(datestring.split()[1].split(':')[2].split('.')[1])
								timestamp = datetime(year, month, day, hour, minute, second, microsecond).timestamp()

							msg = "".join(line.split('|')[1:])
							msg = re.sub(r'# ID:\d+ ', '', msg)
							out.write(f'{timestamp:0<17} | {node:>3} | {msg}')

			elif self.testbed == 'flocklab':
				logging.info('Parsing experiment log of flocklab testbed')
				# Gather all lines of each node.
				nodelog = {}
				for f in self.files:
					# potential encodings: utf-8, iso-8859-1, ascii, ...
					with open(f, 'r', encoding='utf-8') as log:
						lines = log.readlines()
						# The lines of a node could be scattered in the log so we first gather all lines
						# belonging to a node.
						for line in lines:
							# skip csv header line
							if '# timestamp,observer_id,node_id,direction,output' in line:
								continue
							nodeid = int(line.split(',')[1])
							if not nodeid in nodelog:
								nodelog[nodeid] = []
							nodelog[nodeid].append(line)

				# Write formatted log with ascending node IDs.
				with open(self.log_formatted, 'w', encoding='utf-8') as out:
					for node in sorted(nodelog.keys()):
						for line in nodelog[node]:
							timestamp = datetime.fromtimestamp(float(line.split(',')[0])).timestamp()
							msg = "".join(line.split(',')[4:])
							if '\\x' in repr(msg):
								logging.debug(f'Skipping line: {repr(line)}')
								continue
							out.write(f'{timestamp:0<17} | {node:>2} | {msg}')


	def _extract_config(self):
		if self.log_config.exists():
			logging.info(f'{self.log_config} already exists, skipping this step')
		else:
			logging.info(f'Creating {self.log_config}')

			cfg = {'LOG': self.log_formatted, 'DESCRIPTION': self.description, 'NODE_MAPPING': []}
			parameters = ["MX_NUM_NODES", "MX_GENERATION_SIZE", "MX_PAYLOAD_SIZE", "MX_SLOT_LENGTH",
						"MX_ROUND_LENGTH", "MX_PHY_MODE", "MX_SMART_SHUTDOWN_MODE", "MX_TX_PWR_DBM"]

			with open(self.log_formatted, 'r', encoding='utf-8') as log:
				lines = log.readlines()
				for line in lines:
					# list of parameters found in the line (should be one or zero)
					parameter = [word for word in parameters if word in line]
					if len(parameter) > 0:
						parameter = parameter[0]
						cfg[parameter] = int(line.split(parameter)[1].split("=")[1])
						# Remove this parameter from the list after we found it once (all occurrences
						# will be the same).
						parameters.remove(parameter)
						continue
					if "mapped physical node" in line:
						phyID = int(line.split("node")[1].split("to")[0])
						logID = int(line.split("id")[1])
						cfg['NODE_MAPPING'].append((phyID, logID))

				phy_names = ['Invalid', '802.15.4', 'BLE_1M', 'BLE_2M', 'BLE_125k', 'BLE_500k']
				if not 'MX_PHY_MODE' in cfg:
					cfg['MX_PHY_MODE'] = 1
				cfg['MX_PHY_NAME'] = phy_names[cfg['MX_PHY_MODE']]

			with open(self.log_config, 'w', encoding='utf-8') as out:
				cfg['NODE_MAPPING'].sort(key=lambda x: x[1])
				out.write(yaml.dump(cfg))


	# TODO: Different script that have different lines_of_interest will overwrite log_filtered.
	def filter_log(self, lines_of_interest):
		""" Extract interesting lines into a new log. Based on regular expressions.

			lines_of_interest -- a list of regex patterns
		"""

		if self.log_filtered.exists():
			logging.info(f'{self.log_filtered} already exists, skipping this step.')
		else:
			logging.info(f'Creating {self.log_filtered}')

			pattern = r'|'.join([p for p in lines_of_interest])
			with open(self.log_filtered, 'w', encoding='utf-8') as out:
				with open(self.log_formatted, 'r', encoding='utf-8') as log:
					lines = log.readlines()
					pattern = re.compile(pattern)
					for line in lines:
						if pattern.search(line):
							out.write(line)


def main():
	parser = argparse.ArgumentParser()
	parser.add_argument("path", help="path to log directory")
	parser.add_argument("files", help="pattern of file(s) ending, e.g. '*.txt'")
	parser.add_argument("description", help="experiment description (in quotes)")
	parser.add_argument("testbed", help="the parser needs to know the testbed for correct formatting",
						choices=['flocklab', 'graz', 'local'])
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
	files = list(basepath.glob(args.files))

	MixerLogParser(basepath, files, args.description, args.testbed)


if __name__ == "__main__":
	main()
