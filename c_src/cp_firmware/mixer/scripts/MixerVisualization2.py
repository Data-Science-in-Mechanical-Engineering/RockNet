import argparse
import logging
import re
import sys
from collections import namedtuple
from pathlib import Path

import yaml
from matplotlib import cm, colors
from PyQt5.QtCore import (QDateTime, QLineF, QMimeData, QPoint, QRect, QRectF,
                          Qt, QTimer, pyqtSignal)
from PyQt5.QtGui import (QBrush, QColor, QCursor, QDrag, QFont,
                         QLinearGradient, QPainter, QPalette, QPen, QPixmap,
                         QTransform)
from PyQt5.QtWidgets import (QApplication, QFileDialog, QGraphicsItem,
                             QGraphicsLineItem, QGraphicsScene, QGraphicsView,
                             QMainWindow, QMessageBox, QWidget)

from graphical_objects import Link, Node, NodeState
from MixerLogParser import MixerLogParser
from monitor_ui import Ui_MainWindow

#---------------------------------------------------------------------------------------------------
# logging format

fmt	 = '%(asctime)s %(filename)-15.15s:%(lineno)-5d %(levelname)-8s %(message)s'
dfmt = '%H:%M:%S'
logging.basicConfig(format=fmt, datefmt=dfmt)
logger = logging.getLogger('MixerVisualization')

#---------------------------------------------------------------------------------------------------

# TODO: use data classes for newer python versions (>=3.7)
# https://docs.python.org/3/library/dataclasses.html
if sys.version_info >= (3, 7):
	Packet = namedtuple('Packet', ['sender', 'receiver', 'slot', 'flags', 'iv', 'cv'],
 						defaults=[None, None, None, None, None, None])
else:
	Packet = namedtuple('Packet', ['sender', 'receiver', 'slot', 'flags', 'iv', 'cv'])
	Packet.__new__.__defaults__ = (None,) * len(Packet._fields)

#---------------------------------------------------------------------------------------------------

class MyQGraphicsView(QGraphicsView):
	def wheelEvent(self, event):
		self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
		self.setResizeAnchor(QGraphicsView.AnchorUnderMouse)

		zoomFactor = 1.1

		if event.angleDelta().y() > 0:
			self.scale(zoomFactor, zoomFactor)
		else:
			self.scale(1 / zoomFactor, 1 / zoomFactor)

#---------------------------------------------------------------------------------------------------

class MyMainForm (QMainWindow):
	def __init__(self, parent=None):
		QMainWindow.__init__(self, parent)
		self.ui = Ui_MainWindow()
		self.ui.setupUi(self)

		self.ui.loadLogBtn.clicked.connect(self.loadLog)
		self.ui.saveLayoutBtn.clicked.connect(self.saveNodeLayout)
		self.ui.loadLayoutBtn.clicked.connect(self.loadNodeLayout)
		self.ui.applySelBtn.clicked.connect(self.applySelection)
		self.ui.experimentDetailsBtn.clicked.connect(self.experimentDetails)
		self.ui.nextSlotBtn.clicked.connect(lambda: self.updateSlot(1))
		self.ui.prevSlotBtn.clicked.connect(lambda: self.updateSlot(-1))
		self.ui.showNeighborsBox.stateChanged.connect(self.showNeighbors)
		self.ui.showRowsBox.stateChanged.connect(self.showRows)
		self.ui.showRequestsBox.stateChanged.connect(self.showRequests)
		self.ui.showDiscoveryBox.stateChanged.connect(self.showDiscovery)

		# TODO: Implement me
		self.ui.showRxTxBox.setDisabled(True)
		self.ui.showLinksBox.setDisabled(True)

		self.scene = QGraphicsScene()
		self.scene.setBackgroundBrush(Qt.white)
		self.ui.graphicsView.setScene(self.scene)
		self.ui.graphicsView.setDragMode(QGraphicsView.ScrollHandDrag)
		# self.ui.graphicsView.setViewportUpdateMode(QGraphicsView.BoundingRectViewportUpdate)
		self.ui.graphicsView.setViewportUpdateMode(QGraphicsView.FullViewportUpdate)

		self.mlp = None
		# self.cfg = None
		self.packet_log = {}
		self.nodes = {}
		self.colors = cm.get_cmap('tab20').colors
		self.numColors = len(self.colors)

		self.loadedLog = False
		self.loadedLayout = False

#---------------------------------------------------------------------------------------------------

	def showDiscovery(self):
		curState = self.ui.showDiscoveryBox.checkState()
		if curState == Qt.Checked:
			for n in self.nodes.values():
				if n.discoveryPhase:
					n.highlightDiscoveryPhase = True
				else:
					n.highlightDiscoveryPhase = False
				n.update()
		else:
			for n in self.nodes.values():
				n.highlightDiscoveryPhase = False
				n.update()

#---------------------------------------------------------------------------------------------------

	def showRows(self):
		try:
			row = int(self.ui.showRowsLine.text())
		except ValueError:
			# msg = QMessageBox()
			# msg.setText('Enter a correct node ID')
			# msg.exec()
			self.ui.showRowsBox.setCheckState(Qt.Unchecked)
			return

		curState = self.ui.showRowsBox.checkState()
		if curState == Qt.Checked:
			for n in self.nodes.values():
				if row in n.rows:
					n.highlightRows = True
					n.update()
		else:
			for n in self.nodes.values():
				n.highlightRows = False
				n.update()

#---------------------------------------------------------------------------------------------------

	def showRequests(self):
		curState = self.ui.showRequestsBox.checkState()
		if curState == Qt.Checked:
			for item in self.scene.items():
				if type(item) == Link:
					if item.isRequest:
						item.highlightRequest = True
					else:
						item.highlightRequest = False
					item.update()
		else:
			for item in self.scene.items():
				if type(item) == Link:
					item.highlightRequest = False
					item.update()

#---------------------------------------------------------------------------------------------------

	def showNeighbors(self):
		try:
			node = int(self.ui.neighborsLine.text())
		except ValueError:
			# msg = QMessageBox()
			# msg.setText('Enter a correct node ID')
			# msg.exec()
			self.ui.showNeighborsBox.setCheckState(Qt.Unchecked)
			return

		curState = self.ui.showNeighborsBox.checkState()
		if curState == Qt.Checked:
			neighbors = self.nodes[node].neighbors
			for neighbor in neighbors:
				self.nodes[neighbor].highlightNeighbor = True
				self.nodes[neighbor].update()
		else:
			for n in self.nodes.values():
				n.highlightNeighbor = False
				n.update()

		# # reset highlighting
		# for n in self.nodes.values():
		# 	n.highlightNeighbor = False
		# 	n.update()
		#
		# neighbors = self.nodes[node].neighbors
		# for neighbor in neighbors:
		# 	self.nodes[neighbor].highlightNeighbor = True
		# 	self.nodes[neighbor].update()

#---------------------------------------------------------------------------------------------------

	def experimentDetails(self):
		msg = (
			f'Logfile: {self.mlp.exp_config["LOG"]}\n'
			f'\n'
			f'MX_NUM_NODES:             {self.mlp.exp_config["MX_NUM_NODES"]}\n'
			f'MX_GENERATION_SIZE:       {self.mlp.exp_config["MX_GENERATION_SIZE"]}\n'
			f'MX_PAYLOAD_SIZE:          {self.mlp.exp_config["MX_PAYLOAD_SIZE"]}\n'
			f'MX_SLOT_LENGTH:           {self.mlp.exp_config["MX_SLOT_LENGTH"]}\n'
			f'MX_ROUND_LENGTH:          {self.mlp.exp_config["MX_ROUND_LENGTH"]}\n'
			f'MX_PHY_MODE:              {self.mlp.exp_config["MX_PHY_MODE"]} ({self.mlp.exp_config["MX_PHY_NAME"]})\n'
			f'MX_SMART_SHUTDOWN_MODE:   {self.mlp.exp_config["MX_SMART_SHUTDOWN_MODE"]}\n'
			f'\n'
			f'Experiment description:\n'
			f'{self.mlp.exp_config["DESCRIPTION"]}\n'
			f'\n'
			f'Node mapping:\n'
			f'{self.mlp.exp_config["NODE_MAPPING"]}'
		)
		msgBox = QMessageBox()
		msgBox.setFont(QFont("Consolas", 10))
		msgBox.setText(msg)
		msgBox.exec()

#---------------------------------------------------------------------------------------------------

	def updateSlot(self, step):
		slotSelection = self.ui.slotSelText.toPlainText()
		try:
			lastSlot = slotSelection.split(',')[-1]
			if '-' in lastSlot:
				lastSlot = lastSlot.split('-')[1]
			lastSlot = int(lastSlot)
		except ValueError:
			msg = QMessageBox()
			msg.setText('Enter a correct slot selection (e.g. 1-3,7,10-15)')
			msg.exec()
			return

		newSlot = lastSlot + step
		self.ui.slotSelText.setPlainText(str(newSlot))
		self.applySelection()

#---------------------------------------------------------------------------------------------------

	def applySelection(self):
		slotSelection = self.ui.slotSelText.toPlainText()
		slots = []
		try:
			for s in slotSelection.split(','):
				if '-' in s:
					start, end = s.split('-')
					slots.extend(list(range(int(start), int(end) + 1)))
					continue
				slots.append(int(s))
		except ValueError:
			msg = QMessageBox()
			msg.setText('Enter a correct slot selection (e.g. 1-3,7,10-15)')
			msg.exec()
			return

		rnd = self.ui.roundSelBox.value()
		# self.ui.showRequestsBox.setCheckState(Qt.Unchecked)

		# reset node states and remove all links
		for item in self.scene.items():
			if type(item) == Node:
				item.resetState()
				item.update()
				continue
			if type(item) == Link:
				self.scene.removeItem(item)

		packetcolors = {}

		for slot in slots:
			try:
				for packet in self.packet_log[rnd][slot]['packets']:
					# tx packet of the sending node
					if packet.sender == packet.receiver:
						node = self.nodes[packet.sender]
						node.state = NodeState.TX
						# changing the NodeState require a manual update
						# node.update()
						continue

					rxNode = self.nodes[packet.receiver]
					txNode = self.nodes[packet.sender]

					# In case we display a range of slots, a node can be transmitter and receiver. We
					# will then visualize such a node as sender.
					if rxNode.state == NodeState.IDLE:
						rxNode.state = NodeState.RX
					txNode.state = NodeState.TX
					# rxNode.update()
					# txNode.update()

					# Different nodes get different link colors.
					if not txNode in packetcolors:
						packetcolors[txNode] = colors.to_hex(self.colors[len(packetcolors.keys()) % self.numColors])

					isRequest = False
					if packet.flags == 2: # row request
						isRequest = True
					if packet.flags == 3: # column request
						isRequest = True


					# Create link and position it between the source and target nodes.
					link = Link(txNode, rxNode, packetcolors[txNode], isRequest)
					link.setPos(QLineF(txNode.pos(), rxNode.pos()).center())
					self.scene.addItem(link)

			except KeyError as e:
				logger.debug(f'No packets in slot {e}')

			# After adding all links, we update the node state information.
			if slot == slots[-1]:
				try:

					for node, density in self.packet_log[rnd][slot]['neighbors'].items():
						if density == '-':
							self.nodes[node].density = '-'
							self.nodes[node].neighbors = [node]
						else:
							self.nodes[node].density = len(density)
							self.nodes[node].neighbors = density

					for node, discoveryExit in self.packet_log[rnd][slot]['discoveryExit'].items():
						if discoveryExit:
							self.nodes[node].discoveryPhase = False
						else:
							self.nodes[node].discoveryPhase = True

					for node, shutdown in self.packet_log[rnd][slot]['shutdown'].items():
						if shutdown:
							self.nodes[node].shutdown = True
						else:
							self.nodes[node].shutdown = False

					for node, rank in self.packet_log[rnd][slot]['rank'].items():
						self.nodes[node].rank = rank

					for node, rankUp in self.packet_log[rnd][slot]['rankUp'].items():
						self.nodes[node].rankUp = rankUp

					for node, txp in self.packet_log[rnd][slot]['txp'].items():
						if txp == '-':
							self.nodes[node].txp = '-'
						else:
							self.nodes[node].txp = int(round(txp / 65535, 2) * 100)

					for node, rows in self.packet_log[rnd][slot]['rows'].items():
						self.nodes[node].rows = rows

				except KeyError as e:
					print(f'KeyError {e}')

			# Update all nodes.
			for node in self.nodes.values():
				node.update()

			# Update optional highlights
			self.showRequests()
			self.showDiscovery()
			self.showNeighbors()
			self.showRows()

#---------------------------------------------------------------------------------------------------

	def saveNodeLayout(self):
		fileName = QFileDialog.getSaveFileName(self, 'Save Node Layout')[0]
		if not fileName:
			return
		else:
			with open(fileName, 'w') as f:
				for n in self.scene.items():
					if type(n) == Node:
						f.write(f'{n.id},{n.pos().x()},{n.pos().y()}\n')

#---------------------------------------------------------------------------------------------------

	def loadNodeLayout(self):
		# Delete all items in the scene before loading the new layout.
		for item in self.scene.items():
			self.scene.removeItem(item)

		fileName = QFileDialog.getOpenFileName(self, 'Open Node Layout')[0]
		if not fileName:
			return

		with open(fileName, 'r') as f:
			for l in f:
				id, x, y = l.split(',')
				id = int(id)
				x = float(x)
				y = float(y)
				node = Node(id)
				node.setPos(x,y)
				self.scene.addItem(node)
				self.nodes[id] = node

		# Enable buttons in the UI to control the workflow.
		self.loadedLayout = True
		self.ui.saveLayoutBtn.setEnabled(True)
		if self.loadedLog:
			self.ui.applySelBtn.setEnabled(True)
			self.ui.nextSlotBtn.setEnabled(True)
			self.ui.prevSlotBtn.setEnabled(True)

		# Resize the view to show all scene items.
		# TODO does this work? It resizes the scene to the correct size but not the view.
		self.ui.graphicsView.setSceneRect(self.scene.itemsBoundingRect().adjusted(-100,-100,100,100))

#---------------------------------------------------------------------------------------------------

	def loadLog(self):
		path = QFileDialog.getExistingDirectory(self, 'Experiment Directory')
		if not path:
			logger.info('Directory path is empty')
			return

		self.mlp = MixerLogParser(path)
		self.packet_log = {}
		self.ui.loadedLogLbl.setText(f'Loaded Log: {self.mlp.basepath.name}')

		logID_to_phyID = {v: k for (k, v) in self.mlp.exp_config['NODE_MAPPING']}

		with open(self.mlp.log_formatted, 'r', encoding='utf-8') as log:
			lines = log.readlines()
			cur_rnd = None
			cur_slot = None
			cur_node = None
			packet_cnt = 0
			for line in lines:
				# time = float(line.split('|')[0].strip())
				nodeid = int(line.split('|')[1].strip())
				msg = line.split('|')[2].strip()
				res = None

				# After all lines of one node are processed, the next node needs to start clean.
				if cur_node != None and cur_node != nodeid:
					cur_rnd = None
					cur_slot = None
				cur_node = nodeid

				# Current round
				res = re.search(r'(starting round|preparing round) (?P<round>\d+)', msg)
				if res:
					cur_rnd = int(res.group('round'))
					if not cur_rnd in self.packet_log:
						self.packet_log[cur_rnd] = {}
						for slot in range(0, self.mlp.exp_config['MX_ROUND_LENGTH'] + 6): # some offset
							self.packet_log[cur_rnd][slot] = {'rank': {},
															  'txp': {},
															  'packets': [],
															  'rankUp': {},
															  'neighbors': {},
															  'discoveryExit': {},
															  'rows': {},
															  'shutdown': {}}
					continue

				# Skip to the next line if we don't have round information at this point.
				if cur_rnd == None:
					logger.debug(f'Missing round info for line: {repr(line)}')
					continue

				###################################################################################
				# The following information explicitly or implicitly contain information for correct
				# slot association and only require that we know the correct round.
				###################################################################################

				# Packets
				res = re.search(r'(?P<slot>[0-9a-f]+) - (?P<sender>[0-9a-f]+) - (?P<flags>[0-9a-f]+) - (?P<iv>[0-9a-f]+) - (?P<cv>[0-9a-f]+)', msg)
				if res:
					slot = int(res.group('slot'), 16)
					flags = int(res.group('flags'), 16)
					iv = int(res.group('iv'), 16)
					cv = int(res.group('cv'), 16)
					try:
						# get sender id, ignore first bit (used for full rank information)
						sender = logID_to_phyID[int(res.group('sender')[1:], 16)]
						self.packet_log[cur_rnd][slot]['packets'].append(Packet(sender, nodeid, slot, flags, iv, cv))
						self.packet_log[cur_rnd][slot]['neighbors'][nodeid] = set([sender])
					except KeyError as ke:
						logger.error(f'KeyError {ke}, check the log!\nMsg: {msg}\n\tsender {int(res.group("sender")[1:], 16)}\n\tcur_rnd {cur_rnd}\n\tslot {slot}')
						continue

					packet_cnt += 1
					continue

				# Rank up slots
				if 'rank_up_slot=[' in msg:
					rankUpSlots = [int(s) for s in msg.split('=')[1].strip(' \n[]').split(';') if s]
					for r, s in enumerate(rankUpSlots, 1):
						self.packet_log[cur_rnd][s]['rankUp'][nodeid] = True
						self.packet_log[cur_rnd][s]['rank'][nodeid] = r
					continue

				# Rank up rows (information flow)
				if 'rank_up_row=[' in msg:
					rankUpRows = [int(r) for r in msg.split('=')[1].strip(' \n[]').split(';') if r]
					idx = 0
					for rowCnt, row in enumerate(rankUpRows, 1):
						for e, s in enumerate(range(idx, self.mlp.exp_config['MX_ROUND_LENGTH'] + 6), 1):
							if nodeid in self.packet_log[cur_rnd][s]['rankUp']:
								if self.packet_log[cur_rnd][s]['rankUp'][nodeid]:
									if nodeid in self.packet_log[cur_rnd][s]['rows']:
										self.packet_log[cur_rnd][s]['rows'][nodeid].append(row)
									else:
										self.packet_log[cur_rnd][s]['rows'][nodeid] = [row]

									if (s == 0) and (rowCnt < self.packet_log[cur_rnd][s]['rank'][nodeid]):
										idx = 0
									else:
										idx += e

									break
					continue

				# Discovery phase
				res = re.search(r'discovery_exit_slot: (?P<discoveryExit>\d+)', msg)
				if res:
					discoveryExit = int(res.group('discoveryExit'))
					self.packet_log[cur_rnd][discoveryExit]['discoveryExit'][nodeid] = True
					continue

				# Shutdown slot
				res = re.search(r'slot_off: (?P<slotOff>\d+)', msg)
				if res:
					slotOff = int(res.group('slotOff'))
					self.packet_log[cur_rnd][slotOff]['shutdown'][nodeid] = True
					continue

				###################################################################################
				# Beginning from here, we have to know the current slot in order to associate the
				# extracted information correctly.
				###################################################################################

				# Current slot
				res = re.search(r'mixer_update_slot\s*slot (?P<slot>\d+)', msg)
				res2 = re.search(r'RADIO_IRQHandler_\s*\(re\)synchronized to slot (?P<slot>\d+)', msg)
				if res or res2:
					if res:
						cur_slot = int(res.group('slot'))
					else:
						cur_slot = int(res2.group('slot'))
					continue

				# Skip to the next line if we don't have slot information at this point.
				if cur_slot == None:
					logger.debug(f'No slot info for line: {repr(line)}')
					continue

				# TX probability
				res = re.search(r'tx decision p: (?P<txp>\d+)', msg)
				if res:
					txp = int(res.group('txp'))
					self.packet_log[cur_rnd][cur_slot]['txp'][nodeid] = txp
					continue


			logger.info(f'Imported {packet_cnt} packets')

			# Fill missing infos for each round, slot and node in the log.
			all_nodes = list(logID_to_phyID.values())
			all_rounds = list(self.packet_log.keys())
			for rnd in all_rounds:
				all_slots = sorted(list(self.packet_log[rnd].keys()))
				for node in all_nodes:
					last_rank = None
					shutdown = False
					discoveryExit = False
					neighbors = set([node])
					rows = []

					for slot in all_slots:
						# default values we cannot derive for sure
						if not node in self.packet_log[rnd][slot]['txp']:
							self.packet_log[rnd][slot]['txp'][node] = '-'

						if not node in self.packet_log[rnd][slot]['rankUp']:
							self.packet_log[rnd][slot]['rankUp'][node] = False

						# add up nodes from received packets to neighbor set
						if not node in self.packet_log[rnd][slot]['neighbors']:
							self.packet_log[rnd][slot]['neighbors'][node] = neighbors.copy()
						else:
							neighbors |= self.packet_log[rnd][slot]['neighbors'][node]
							self.packet_log[rnd][slot]['neighbors'][node] = neighbors.copy()

						# build up the set of rank up rows
						if not node in self.packet_log[rnd][slot]['rows']:
							self.packet_log[rnd][slot]['rows'][node] = rows.copy()
						else:
							rows.extend(self.packet_log[rnd][slot]['rows'][node])
							self.packet_log[rnd][slot]['rows'][node] = rows.copy()

						# rank is monotonically increasing so we can fill missing rank information with previous infos
						if not node in self.packet_log[rnd][slot]['rank']:
							if last_rank == None:
								# TODO: Initial rank is based on message distribution.
								self.packet_log[rnd][slot]['rank'][node] = 0
							else:
								self.packet_log[rnd][slot]['rank'][node] = last_rank
						else:
							last_rank = self.packet_log[rnd][slot]['rank'][node]

						# discovery exit is false during discovery phase
						if not node in self.packet_log[rnd][slot]['discoveryExit']:
							self.packet_log[rnd][slot]['discoveryExit'][node] = discoveryExit
						else:
							if self.packet_log[rnd][slot]['discoveryExit'][node] == False:
								logger.error('discoveryExit value must be True at this point!')
							discoveryExit = True

						if not node in self.packet_log[rnd][slot]['shutdown']:
							self.packet_log[rnd][slot]['shutdown'][node] = shutdown
						else:
							if self.packet_log[rnd][slot]['shutdown'][node] == False:
								logger.error('shutdown value must be True at this point!')
							shutdown = True

		# Enable buttons in the UI to control the workflow.
		self.loadedLog = True
		self.ui.experimentDetailsBtn.setEnabled(True)
		if self.loadedLayout:
			self.ui.applySelBtn.setEnabled(True)
			self.ui.nextSlotBtn.setEnabled(True)
			self.ui.prevSlotBtn.setEnabled(True)

#---------------------------------------------------------------------------------------------------

if __name__ == '__main__':
	parser = argparse.ArgumentParser()
	parser.add_argument("--lvl", help="specifies log level", choices=['INFO', 'DEBUG'])
	args = parser.parse_args()

	if not args.lvl:
		logger.setLevel(logging.INFO)
	elif args.lvl == 'INFO':
		logger.setLevel(logging.INFO)
	elif args.lvl == 'DEBUG':
		logger.setLevel(logging.DEBUG)
	else:
		logger.critical('Unknown log level')
		sys.exit()

	app = QApplication(sys.argv)
	mainWindow = MyMainForm()
	mainWindow.show()
	sys.exit(app.exec_())
