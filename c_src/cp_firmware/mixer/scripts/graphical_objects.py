from enum import Enum

from colour import Color
from PyQt5.QtCore import QLineF, QPointF, QRectF, Qt
from PyQt5.QtGui import QColor, QFont, QPainter, QPen, QTransform
from PyQt5.QtWidgets import QGraphicsItem, QGraphicsLineItem


class NodeState(Enum):
	IDLE = 1
	RX = 2
	TX = 3


class StateColor(Enum):
	IDLE = Qt.white
	RX = QColor('#def0aa') # QColor('#d0f062') c7deaf
	TX = QColor('#afd1de') # QColor('#87cbf5')
	RANKUP = QColor('#a4d66f') # QColor('#548f24')a4d66f
	DISCOVERY = QColor('#f29d49') # QColor('#d69c9c')
	NEIGHBOR = QColor('#f0e91d') # QColor('#d69c9c')
	SHUTDOWN = QColor('#c9c9c9')
	ROW = QColor('#ad2d2d')

#  ------------------
# | NodeID |   Rank  |
# |--------|---------|
# |  TX_P  | Density |
#  ------------------

class Node(QGraphicsItem):
	def __init__(self, id):
		super(Node, self).__init__()
		self.setCursor(Qt.OpenHandCursor)
		self.setAcceptedMouseButtons(Qt.LeftButton)
		self.setFlag(QGraphicsItem.ItemIsMovable)
		self.setZValue(1)

		self.idleColor = StateColor.IDLE.value
		self.rxColor = StateColor.RX.value
		self.txColor = StateColor.TX.value
		self.rankupColor = StateColor.RANKUP.value
		self.discoveryColor = StateColor.DISCOVERY.value
		self.neighborColor = StateColor.NEIGHBOR.value
		self.shutdownColor = StateColor.SHUTDOWN.value
		self.rowColor = StateColor.ROW.value

		self.id = id
		self.density = 1
		self.neighbors = []
		self.rank = 0
		self.rankUp = False
		self.txp = '-'
		self.state = NodeState.IDLE
		self.discoveryPhase = False
		self.shutdown = False
		self.rows = []

		self.highlightDiscoveryPhase = False
		self.highlightNeighbor = False
		self.highlightRows = False

		self.penColor = Qt.black
		self.penWidth = 2

		self.baseBoundRect = QRectF(0, 0, 75, 50)
		self.discoveryBoundRect = QRectF(75, 0, 15, 50)
		self.neighborBoundRect = QRectF(-15, 0, 15, 50)
		self.rowBoundRect = QRectF(0, -10, 10, 10)


		# Nodes should always appear in the same way and ignore scalings etc.
		# self.setFlag(QGraphicsItem.ItemIgnoresTransformations, enabled=True)

	def resetState(self):
		self.state = NodeState.IDLE
		self.highlightDiscoveryPhase = False
		self.highlightNeighbor = False
		self.highlightRows = False

	def boundingRect(self):
		# return self.baseBoundRect
		bRect = self.baseBoundRect
		if self.highlightDiscoveryPhase:
			bRect = bRect.united(self.discoveryBoundRect)
		if self.highlightNeighbor:
			bRect = bRect.united(self.neighborBoundRect)
		if self.highlightRows:
			bRect = bRect.united(self.rowBoundRect)
		return bRect

	def paint(self, painter, option, widget):
		painter.setRenderHint(QPainter.Antialiasing, True)

		# if self.discoveryPhase

		# if self.highlightNeighbor:
		# 	self.penColor = Qt.red
		# 	self.penWidth = 5
		# else:
		# 	self.penColor = Qt.black
		# 	self.penWidth = 2
		if self.shutdown:
			painter.setPen(QPen(self.penColor, self.penWidth))
			painter.setBrush(self.shutdownColor)
		elif self.state == NodeState.IDLE:
			painter.setPen(QPen(self.penColor, self.penWidth))
			painter.setBrush(self.idleColor)
		elif self.state == NodeState.RX:
			painter.setPen(QPen(self.penColor, self.penWidth))
			if self.rankUp:
				painter.setBrush(self.rankupColor)
			else:
				painter.setBrush(self.rxColor)
		else: #TX
			painter.setPen(QPen(self.penColor, self.penWidth))
			painter.setBrush(self.txColor)

		painter.setFont(QFont('Consolas', 12, QFont.Normal))
		painter.drawRect(0, 0, 50, 25)
		painter.drawText(0, 0, 50, 25, Qt.AlignCenter, str(self.id))

		if self.highlightDiscoveryPhase:
			painter.save()
			painter.setBrush(self.discoveryColor)
			painter.drawRect(self.discoveryBoundRect)
			painter.restore()

		if self.highlightRows:
			painter.save()
			painter.setBrush(self.rowColor)
			painter.drawRect(self.rowBoundRect)
			painter.restore()
		# 	self.baseBoundRect = QRectF(0, 0, 87, 50)
		# else:
		# 	self.baseBoundRect = QRectF(0, 0, 75, 50)
		# 	painter.drawRect(0, 25, 50, 25)
		painter.drawRect(0, 25, 50, 25)

		# if self.highlightDiscoveryPhase:
		# 	painter.save()
		# 	painter.setBrush(QColor('#d69c9c'))
		# 	painter.drawRect(0, 25, 50, 25)
		# 	painter.restore()
		# else:
		# 	painter.drawRect(0, 25, 50, 25)

		painter.drawText(0, 25, 50, 25, Qt.AlignCenter, f'{str(self.txp)}%')

		painter.drawRect(50, 0, 25, 25)
		painter.drawText(50, 0, 25, 25, Qt.AlignCenter, str(self.rank))
		# if self.rankUp:
		# 	painter.setFont(QFont('Consolas', 12, QFont.Bold))
		# 	painter.drawText(50, 0, 25, 25, Qt.AlignCenter, str(self.rank))
		# 	painter.setFont(QFont('Consolas', 12, QFont.Normal))
		# else:
		# 	painter.drawText(50, 0, 25, 25, Qt.AlignCenter, str(self.rank))

		if self.highlightNeighbor:
			painter.save()
			painter.setBrush(self.neighborColor)
			painter.drawRect(self.neighborBoundRect)
			painter.restore()
		# else:
		# 	painter.drawRect(50, 25, 25, 25)
		painter.drawRect(50, 25, 25, 25)
		# if self.highlightNeighbor:
		# 	painter.save()
		# 	painter.setBrush(self.neighborColor)
		# 	painter.drawRect(50, 25, 25, 25)
		# 	painter.restore()
		# else:
		# 	painter.drawRect(50, 25, 25, 25)
		painter.drawText(50, 25, 25, 25, Qt.AlignCenter, str(self.density))


class Link(QGraphicsItem):
	def __init__(self, source, target, color, isRequest):
		super(Link, self).__init__()
		self.source = source
		self.target = target
		self.color = color
		# self.packet = packet

		self.isRequest = isRequest
		self.highlightRequest = False

		self.pen = QPen()
		self.pen.setWidth(2)
		self.pen.setColor(QColor(self.color))
		# Cosmetic prevents a change of line width when the view is scaled.
		self.pen.setCosmetic(True)

		# self.line = QLineF(self.source.pos() - QPointF(0, self.source.diameter / 2),
		# 				   self.target.pos() + QPointF(0, self.source.diameter / 2))
		self.line = QLineF(self.source.pos(),
						   self.target.pos() + QPointF(0, 50))
		# Move the center point of the line into the local origin and adjust for placing the line
		# between both nodes from the application.
		self.line.translate(self.line.center() * -1 + QPointF(0, 25))

		self.top = min(self.line.p1().y(), self.line.p2().y())
		self.left = min(self.line.p1().x(), self.line.p2().x())

		self.baseBoundRect = QRectF(self.left, self.top,
								abs(self.line.dx()), abs(self.line.dy()))


	def boundingRect(self):
		return self.baseBoundRect


	def paint(self, painter, option, widget):
		painter.setRenderHint(QPainter.Antialiasing, True)
		if self.highlightRequest:
			self.pen.setWidth(6)
		else:
			self.pen.setWidth(2)
		painter.setPen(self.pen)
		painter.drawLine(self.line)
