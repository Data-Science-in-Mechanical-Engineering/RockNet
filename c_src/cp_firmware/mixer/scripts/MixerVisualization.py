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
		self.ui.showRequestsBox.stateChanged.connect(self.showRequests)
		self.ui.showDiscoveryBox.stateChanged.connect(self.showDiscovery)

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
				item.state = NodeState.IDLE
				# TODO: reset function in Node class
				item.highlightNeighbor = False
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
				logging.debug(f'No packets in slot {e}')

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

					# for node, neighbors in self.packet_log[rnd][slot]['neighbors'].items():
					# 	print(f'neighbors of {node} are {neighbors}')

					for node, discoveryExit in self.packet_log[rnd][slot]['discoveryExit'].items():
						if discoveryExit > 0:
							self.nodes[node].discoveryPhase = True
						else:
							self.nodes[node].discoveryPhase = False

					for node, rank in self.packet_log[rnd][slot]['rank'].items():
						self.nodes[node].rank = rank

					for node, rankUp in self.packet_log[rnd][slot]['rankUp'].items():
						self.nodes[node].rankUp = rankUp

					for node, txp in self.packet_log[rnd][slot]['txp'].items():
						if txp == '-':
							self.nodes[node].txp = '-'
						else:
							self.nodes[node].txp = int(round(txp / 65535, 2) * 100)

				except KeyError as e:
					print(f'KeyError {e}')

			# Update all nodes.
			for node in self.nodes.values():
				node.update()

			# Update optional highlights
			self.showRequests()
			self.showDiscovery()
			self.showNeighbors()

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
		# TODO does this work?
		self.ui.graphicsView.setSceneRect(self.scene.itemsBoundingRect())

#---------------------------------------------------------------------------------------------------

	def loadLog(self):
		path = QFileDialog.getExistingDirectory(self, 'Experiment Directory')
		if not path:
			logging.info('Directory path is empty')
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
			# backlog = {'rank': {}, 'txp': {}, 'neighbors': {}, 'discoveryExit': {}} #TODO: shutdown
			packet_cnt = 0
			for line in lines:
				# time = float(line.split('|')[0].strip())
				nodeid = int(line.split('|')[1].strip())
				msg = line.split('|')[2].strip()

				# After all lines of one node are processed, the next node needs to start clean.
				if cur_node != None and cur_node != nodeid:
					cur_rnd = None
					cur_slot = None
				cur_node = nodeid

				# Current round
				res = re.search(r'starting round (?P<round>\d+)', msg)
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
															  'shutdown': {}}
					continue

				# Skip to the next line if we don't have round information at this point.
				if cur_rnd == None:
					logging.debug(f'Missing round info for line: {repr(line)}')
					continue

				# Packets (no cur_slot info required)
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
					except KeyError as ke:
						print(f'KeyError {ke}, check the log!\nMsg: {msg}\n\tsender {int(res.group("sender")[1:], 16)}\n\tcur_rnd {cur_rnd}\n\tslot {slot}')
						continue

					packet_cnt += 1
					continue

				# Rank up slots (no cur_slot info required)
				if 'rank_up_slot=[' in msg:
					rankUpSlots = [int(s) for s in msg.split('=')[1].strip(' \n[]').split(';') if s]
					for s in rankUpSlots:
						self.packet_log[cur_rnd][s]['rankUp'][nodeid] = True
					continue

				# Current slot
				res = re.search(r'mixer_update_slot\s*slot (?P<slot>\d+)', msg)
				res2 = re.search(r'RADIO_IRQHandler_\s*\(re\)synchronized to slot (?P<slot>\d+)', msg)
				if res or res2:
					if res:
						cur_slot = int(res.group('slot'))
					else:
						cur_slot = int(res2.group('slot'))
					# # When a node receives something for the first time, some information are
					# # printed without a prior slot information. We put these information into a
					# # backlog and add them to the previous slot here.
					# prev_slot = cur_slot - 1
					# for node, rank in backlog['rank'].items():
					# 	print(f'Backlog: Adding rank info from node {node} to slot {prev_slot}')
					# 	self.packet_log[cur_rnd][prev_slot]['rank'][node] = rank
					# for node, txp in backlog['txp'].items():
					# 	print(f'Backlog: Adding txp info from node {node} to slot {prev_slot}')
					# 	self.packet_log[cur_rnd][prev_slot]['txp'][node] = txp
					# for node, neighbors in backlog['neighbors'].items():
					# 	print(f'Backlog: Adding neighbor info from node {node} to slot {prev_slot}')
					# 	self.packet_log[cur_rnd][prev_slot]['neighbors'][node] = neighbors
					# for node, discoveryExit in backlog['discoveryExit'].items():
					# 	print(f'Backlog: Adding discoveryExit info from node {node} to slot {prev_slot}')
					# 	self.packet_log[cur_rnd][prev_slot]['discoveryExit'][node] = discoveryExit
					#
					# backlog = {'rank': {}, 'txp': {}, 'neighbors': {}, 'discoveryExit': {}}
					continue

				# Skip to the next line if we don't have slot information at this point.
				if cur_slot == None:
					logging.debug(f'No slot info for line: {repr(line)}')
					continue

				res = re.search(r'(mixer_update_slot\s*smart shutdown initiated\n)', msg)
				if res:
					self.packet_log[cur_rnd][cur_slot]['shutdown'][nodeid] = True
					continue

				# History (density)
				res = re.search(r'mixer_update_slot\s*history\s*(?P<neighborID>\d+)', msg)
				if res:
					# neighborID = logID_to_phyID[int(res.group('neighborID'))]
					# if cur_slot == None:
					# 	if not nodeid in backlog['neighbors']:
					# 		backlog['neighbors'][nodeid] = [nodeid]
					# 	backlog['neighbors'][nodeid].append(neighborID)
					# else:
					# 	if not nodeid in self.packet_log[cur_rnd][cur_slot]['neighbors']:
					# 		self.packet_log[cur_rnd][cur_slot]['neighbors'][nodeid] = [nodeid]
					# 	self.packet_log[cur_rnd][cur_slot]['neighbors'][nodeid].append(neighborID)

					neighborID = logID_to_phyID[int(res.group('neighborID'))]
					if not nodeid in self.packet_log[cur_rnd][cur_slot]['neighbors']:
						self.packet_log[cur_rnd][cur_slot]['neighbors'][nodeid] = [nodeid]
					self.packet_log[cur_rnd][cur_slot]['neighbors'][nodeid].append(neighborID)
					continue

				# Discovery phase
				res = re.search(r'mixer_update_slot\s*discovery exit slot: (?P<discoveryExit>\d+)', msg)
				if res:
					discoveryExit = int(res.group('discoveryExit'))
					# if cur_slot == None:
					# 	backlog['discoveryExit'][nodeid] = discoveryExit
					# 	continue
					self.packet_log[cur_rnd][cur_slot]['discoveryExit'][nodeid] = discoveryExit
					continue

				# TX probability
				res = re.search(r'tx decision p: (?P<txp>\d+)', msg)
				if res:
					txp = int(res.group('txp'))
					# if cur_slot == None:
					# 	backlog['txp'][nodeid] = txp
					# 	continue
					self.packet_log[cur_rnd][cur_slot]['txp'][nodeid] = txp
					continue

				# Rank
				res = re.search(r'new row \d+, rank: (?P<rank>\d+)', msg)
				if res:
					rank = int(res.group('rank'))
					# if cur_slot == None:
					# 	backlog['rank'][nodeid] = rank
					# 	continue
					self.packet_log[cur_rnd][cur_slot]['rank'][nodeid] = rank
					continue

			logging.info(f'Imported {packet_cnt} packets')

			# Fill missing infos for each round, slot and node in the log.
			all_nodes = list(logID_to_phyID.values())
			all_rounds = list(self.packet_log.keys())
			for rnd in all_rounds:
				all_slots = sorted(list(self.packet_log[rnd].keys()))
				for node in all_nodes:
					last_rank = None
					last_discoveryExit = None
					last_shutdown = None

					for slot in all_slots:
						# default values we cannot derive for sure
						if not node in self.packet_log[rnd][slot]['txp']:
							self.packet_log[rnd][slot]['txp'][node] = '-'

						if not node in self.packet_log[rnd][slot]['neighbors']:
							self.packet_log[rnd][slot]['neighbors'][node] = '-'

						if not node in self.packet_log[rnd][slot]['rankUp']:
							self.packet_log[rnd][slot]['rankUp'][node] = False


						# rank is monotonically increasing so we can fill missing rank information with previous infos
						if not node in self.packet_log[rnd][slot]['rank']:
							if last_rank == None:
								# TODO: Initial rank is based on message distribution.
								self.packet_log[rnd][slot]['rank'][node] = 0
							else:
								self.packet_log[rnd][slot]['rank'][node] = last_rank
						else:
							last_rank = self.packet_log[rnd][slot]['rank'][node]

						# discovery exit slot is monotonically increasing
						if not node in self.packet_log[rnd][slot]['discoveryExit']:
							if last_discoveryExit == None:
								# this may happen at the beginning, fill discovery info with 1
								# print(f'Beginning: node {node}, rnd {rnd}, slot {slot}, discoveryExit 1')
								self.packet_log[rnd][slot]['discoveryExit'][node] = 1
							elif slot < last_discoveryExit:
								# in case discovery exit infos are missing during discovery phase
								# print(f'Between: node {node}, rnd {rnd}, slot {slot}, discoveryExit {last_discoveryExit}')
								self.packet_log[rnd][slot]['discoveryExit'][node] = last_discoveryExit
							else:
								# after discovery phase, fill discovery info with 0
								# print(f'End: node {node}, rnd {rnd}, slot {slot}, discoveryExit 0')
								self.packet_log[rnd][slot]['discoveryExit'][node] = 0
						else:
							last_discoveryExit = self.packet_log[rnd][slot]['discoveryExit'][node]

						if not node in self.packet_log[rnd][slot]['shutdown']:
							if last_shutdown == None:
								self.packet_log[rnd][slot]['shutdown'][node] = False
							else:
								self.packet_log[rnd][slot]['shutdown'][node] = last_shutdown
						else:
							last_shutdown = self.packet_log[rnd][slot]['shutdown'][node]

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

	# logging format
	fmt	 = '%(asctime)s %(levelname)-8s %(message)s'
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

	app = QApplication(sys.argv)
	mainWindow = MyMainForm()
	mainWindow.show()
	sys.exit(app.exec_())
