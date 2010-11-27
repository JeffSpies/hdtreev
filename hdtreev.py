#!/usr/bin/env python

__author__ = "Jeffrey R. Spies"
__copyright__ = "Copyright 2005-2010, Jeffrey R. Spies"
__license__ = "Apache License, Version 2.0"
__version__ = "0.32"
__maintainer__ = "Jeffrey R. Spies"
__email__ = "jspies@virginia.edu"
__status__ = "Beta"

#########################################################################################

# TODO Tighten all code up in terms of modularity
# TODO Refactor memory profile
# TODO SmatterJitter Group selected and init
# TODO Painting
# TODO Serialize (Open/Save: on match datafile then locations, label, display)
# TODO Export needs more work; SVG, PDF; Scroll bars
# TODO Update spinbox when undo
# TODO Missingness: imputation currently
# TODO Expand for labels

#########################################################################################

from PyQt4 import QtCore, QtGui
import math, random, csv, copy

#########################################################################################

class Tree(QtGui.QGraphicsItem):
    labelBottomSpace = 15.0
    def __init__(self, dispatch, data, select, x=None, y=None):
        super(self.__class__, self).__init__()
        
        self.dispatch = dispatch
        
        self.setFlag(QtGui.QGraphicsItem.ItemIsMovable, True)
        self.setFlag(QtGui.QGraphicsItem.ItemIsSelectable, True)
        self.setCacheMode(QtGui.QGraphicsItem.DeviceCoordinateCache)
        self.setFlag(QtGui.QGraphicsItem.ItemSendsGeometryChanges)
        
        self.adjust()
        
        self.matrix = QtGui.QMatrix()
        self.factor = 1
        self.textRect = None
        
        self.color = QtCore.Qt.black
        
        self.selectedPen = QtGui.QPen(QtCore.Qt.red, 1, QtCore.Qt.SolidLine,
            QtCore.Qt.RoundCap, QtCore.Qt.MiterJoin)
        
        self.select = select
        self.data = data # Raw data of all types
        metadata = self.dispatch.metadata
        self.transformedData = copy.copy(data) # Transformed data for icon use
        
        self.isMissing =[]
        
        for i in range(0, len(metadata['isNumeric'])):
            if self.data[i]:
                self.transformedData[i] = (self.data[i]-metadata['means'][i])/metadata['sds'][i] + metadata['stdmins'][i] + 5.0
                self.isMissing.append(False)
            else:
                # mean imputation
                self.transformedData[i] = metadata['means'][i]/metadata['sds'][i] + metadata['stdmins'][i] + 5.0
                self.isMissing.append(True)
        
        self.row = [self.transformedData[i] for i in self.select]
        
        self.createIcon()
        
        if x == None:
            # TODO smart jitter
            x = 0
        
        if y == None:
            # TODO smart jitter
            y = 0
        
        self.setPos(x, y)
    
    def getPen(self):
        pen = QtGui.QPen(self.color, 1, QtCore.Qt.SolidLine, QtCore.Qt.RoundCap, QtCore.Qt.MiterJoin)
        return pen
    
    def boundingRect(self):
        return self.rect
    
    def adjust(self):
        self.prepareGeometryChange()
    
    def itemChange(self, change, value):
        #if change == QtGui.QGraphicsItem.ItemPositionChange:
        #    print self.pos()
        return super(Tree, self).itemChange(change, value)
    
    def createIcon(self):
        self.opath = QtGui.QPainterPath()
        node = 1         # starts at 1
        level = 0 # starts at 0
        xsum = 0
        ysum = self.row[0]
        prevLevel = []
        prevLevel.append((xsum, ysum))
        currentLevel = []
        self.opath.lineTo(xsum, ysum)
        
        isRight = True
        level = 1
        nodeAtLevel = 0
        countAtEachPrevLevelNode = 0
        
        self.xMax = 0.0
        self.xMin = 0.0
        
        if len(self.row) > 1:
            if len(self.row) % 2: # if odd
                to = len(self.row)
            else:
                to = len(self.row)-1
            for i in range(1, to, 2):
                if isRight:
                    xsum += self.row[i]
                    isRight = False
                else:
                    xsum -= self.row[i]
                    isRight = True
            
                ysum += self.row[i+1]
                self.opath.lineTo(xsum, ysum)
            
                if xsum > self.xMax:
                    self.xMax = xsum
                elif xsum < self.xMin:
                    self.xMin = xsum
            
                currentLevel.append((xsum, ysum))
            
                if countAtEachPrevLevelNode < 1: # 2 branches per node
                    countAtEachPrevLevelNode += 1
                else:
                    nodeAtLevel += 1 # more than 2? move on to next node
                    if nodeAtLevel >= int(math.pow(2, level-1)):
                        level += 1
                        prevLevel = currentLevel
                        currentLevel = []
                        nodeAtLevel = 0
            
                    countAtEachPrevLevelNode = 0
            
                xsum = prevLevel[nodeAtLevel][0]
                ysum = prevLevel[nodeAtLevel][1]
                self.opath.moveTo(xsum,ysum)
        
        tMin = self.xMin             # Rotation
        self.xMin = self.xMax        # Rotation
        self.xMax = tMin             # Rotation
        
        #self.opath.translate(self.pos().x(), self.pos().y())
        matrix = QtGui.QMatrix()
        matrix.rotate(180)
        self.opath = matrix.map(self.opath)
    
    def updateSelect(self, select):
        self.select = select
        self.row = []
        for i in self.select:
            if i in self.dispatch.metadata['isNumeric']:
                self.row.append(self.transformedData[i])
        if len(self.row) > 0:
            self.createIcon()
            self.zoom(1)
            self.update()
    
    def zoom(self, factor):
        self.factor *= factor
        self.setPos(self.pos().x()*factor, self.pos().y()*factor)
        self.matrix.scale(factor, factor)
        self.update()
    
    def update(self):
        self.path = self.matrix.map(self.opath)
        self.rect = self.path.boundingRect().normalized()
        if self.hasLabel():
            self.rect.setBottom(self.rect.bottom()+Tree.labelBottomSpace)
        super(Tree, self).update()
    
    def hasLabel(self):
        return not self.dispatch.labelIndex == None
    
    def paint(self, painter, option, widget):
        painter.setPen(self.getPen())
        
        if self.isSelected():
            painter.setPen(self.selectedPen)
            painter.drawRect(self.boundingRect())
            painter.setPen(self.getPen())
        
        painter.setPen(self.getPen())
        
        painter.drawPath(self.path)
        
        xMin = self.xMin*self.factor
        xMax = self.xMax*self.factor
        
        if self.hasLabel():
            value = self.data[self.dispatch.labelIndex]
            if isinstance(value, float):
                value = round(value, 3) # TODO setting for rounding floats
            
            tRect = copy.copy(self.rect)
            
            if xMax > abs(xMin):
                tRect.moveLeft((xMax-abs(xMin))/2.0)
            elif xMax < abs(xMin):
                tRect.moveRight((abs(xMin)-xMax)/2.0)
                
            self.textRect = painter.drawText(tRect, QtCore.Qt.AlignCenter | QtCore.Qt.AlignBottom, str(value))
            #if self.textRect.right() > self.rect.right():
            #    self.rect.setRight(self.textRect.right())
            #if self.textRect.left() < self.rect.left():
            #    self.rect.setLeft(self.textRect.left())

#########################################################################################

class VariableRow(QtGui.QTreeWidgetItem):
    def __init__(self, index, variable, typ):
        super(self.__class__, self).__init__([str(index), str(variable), str(typ)])
        self.setFlags(
            QtCore.Qt.ItemIsSelectable | 
            QtCore.Qt.ItemIsEnabled | 
            QtCore.Qt.ItemIsUserCheckable
        )

class VariableTable(QtGui.QTreeWidget):
    def __init__(self, dispatch):
        super(self.__class__, self).__init__()
        self.dispatch = dispatch
        
        self.indexTotal = 0
        
        labels = ['Index', 'Variable', 'Type']
        self.setHeaderLabels(labels)
        self.setColumnCount(len(labels))
        self.setSortingEnabled(True)
        
        self.setSelectionMode(QtGui.QAbstractItemView.ExtendedSelection)
        self.setColumnHidden(0, True)
        
        self.setAlternatingRowColors(True)
        
        self.items = []
        
        self.itemSelectionChanged.connect(self.variablesUsedChanged)
    
    def addItem(self, variable, typ):
        item = VariableRow(self.indexTotal, variable, typ)
        self.addTopLevelItem(item)
        self.items.append(item)
        self.indexTotal += 1
    
    def selectAll(self):
        for i in self.items:
            self.setItemSelected(i, True)
    
    @QtCore.pyqtSlot()
    def variablesUsedChanged(self):
        self.dispatch.variablesUsedChanged([int(i.text(0)) for i in self.selectedItems()])

#########################################################################################

class ControlPanel(QtGui.QWidget):
    def __init__(self, dispatch):
        super(self.__class__, self).__init__()
        
        self.dispatch = dispatch
        
        formLayout = QtGui.QFormLayout()
        
        #################################################################################
        
        self.dataFileRead = QtGui.QLineEdit()
        self.dataFileRead.setReadOnly(True)
        formLayout.addRow('Data File', self.dataFileRead)
        
        #################################################################################
        
        self.variablesDisplayed = VariableTable(self.dispatch)
        formLayout.addRow('Display Variables', self.variablesDisplayed)
        
        #################################################################################
        
        self.labelVariable = QtGui.QComboBox()
        self.labelVariable.currentIndexChanged.connect(self.labelChanged)
        formLayout.addRow('Label Variable', self.labelVariable)
        
        #################################################################################
        
        self.displayLabel = QtGui.QCheckBox()
        self.displayLabel.stateChanged.connect(self.labelCheckBoxChanged)
        formLayout.addRow('Display Label', self.displayLabel)
        
        #################################################################################
        
        # self.shuffleWidget = QtGui.QWidget()
        # self.shuffleLayout = QtGui.QHBoxLayout()
        
        self.shuffleNumber = QtGui.QSpinBox()
        self.shuffleNumber.setMaximum(int(math.pow(2, 31)-1))
        self.dispatch.shuffleSeed = 0
        self.shuffleNumber.valueChanged.connect(self.sbValueChanged)
        #self.shuffleLayout.addWidget(self.shuffleNumber)
        
        #self.shuffleFavoriteButton = QtGui.QPushButton(">")
        #self.shuffleLayout.addWidget(self.shuffleFavoriteButton)
        
        #self.shuffleFavorite = QtGui.QSpinBox()
        #self.shuffleFavorite.setSpecialValueText(' ')
        #self.shuffleLayout.addWidget(self.shuffleFavorite)
        
        #self.shuffleWidget.setLayout(self.shuffleLayout)
        formLayout.addRow('Shuffle Seed', self.shuffleNumber)
        
        self.multiply = QtGui.QSpinBox()
        self.multiply.setMinimum(int(1))
        self.multiply.setMaximum(int(math.pow(2, 31)-1))
        self.dispatch.multiple = 1
        self.multiply.valueChanged.connect(self.multipleValueChanged)
        formLayout.addRow('Multiply Variables', self.multiply)
        
        self.setLayout(formLayout)
    
    @QtCore.pyqtSlot()
    def seedChanged(self):
        if str(self.seedEdit.text()).strip() == '':
            self.seedEdit.setText(self.seed)
        else:
            self.seed = self.seedEdit.text()
    
    @QtCore.pyqtSlot(int)
    def sbValueChanged(self, i):
        self.dispatch.shuffleNumberChanged(self.dispatch.shuffleSeed, i)
    
    @QtCore.pyqtSlot(int)
    def multipleValueChanged(self, i):
        self.dispatch.multipleChanged(self.dispatch.multipleChanged, i)
    
    #@QtCore.pyqtSlot(int)
    #def variableXChanged(self, index):
    #    pass
    #
    #@QtCore.pyqtSlot(int)
    #def variableYChanged(self, index):
    #    pass
    
    @QtCore.pyqtSlot(int)    
    def labelChanged(self, index):
        self.dispatch.labelChanged(index)
    
    @QtCore.pyqtSlot(int)    
    def labelCheckBoxChanged(self, state):
        self.dispatch.labelCheckBoxChanged(state)

#########################################################################################

class GraphWidget(QtGui.QGraphicsView):
    def __init__(self, dispatch):
        super(self.__class__, self).__init__()
        self.setViewportUpdateMode(QtGui.QGraphicsView.BoundingRectViewportUpdate)
        self.setRenderHint(QtGui.QPainter.Antialiasing)
        self.setTransformationAnchor(QtGui.QGraphicsView.AnchorUnderMouse)
        self.setResizeAnchor(QtGui.QGraphicsView.AnchorViewCenter)
        self.setDragMode(QtGui.QGraphicsView.RubberBandDrag)

        self.scene = QtGui.QGraphicsScene(self)
        self.scene.setItemIndexMethod(QtGui.QGraphicsScene.NoIndex) # if dynamic scene

        self.setScene(self.scene)
        self.setBackgroundBrush(QtCore.Qt.white);
    
    def keyPressEvent(self, event):
        if event.key() == QtCore.Qt.Key_Shift:
            self.setDragMode(QtGui.QGraphicsView.ScrollHandDrag)
    
    def keyReleaseEvent(self, event):
        if event.key() == QtCore.Qt.Key_Shift:
            self.setDragMode(QtGui.QGraphicsView.RubberBandDrag)
    
    def wheelEvent(self, event):
        self.scaleIcons(math.pow(2.0, -event.delta() / 240.0))
        self.update()
    
    def scaleIcons(self, scaleFactor):
        #factor = self.matrix().scale(scaleFactor, scaleFactor).mapRect(QtCore.QRectF(0, 0, 1, 1)).width()
        for i in self.scene.items():
            i.zoom(scaleFactor)

#########################################################################################
# COMMANDS
#########################################################################################

class VariablesUsedChanged(QtGui.QUndoCommand):
    def __init__(self, dispatch, items, description):
        super(self.__class__, self).__init__(description)
        self.dispatch = dispatch
        self.description = description
        
        self.new = items
        self.old = copy.deepcopy(self.dispatch.variablesUsed)
    
    def redo(self):
        self.dispatch.variablesUsed = self.new
        self.dispatch.variablesUsed.sort()
        
        self.dispatch.regenerateIcons()
        
        #random.seed(self.dispatch.shuffleSeed)
        #shuffled = copy.copy(self.dispatch.variablesUsed) # selected columns
        #random.shuffle(shuffled)
        #for i in self.dispatch.graph.scene.items():
        #    i.updateSelect(shuffled)
        #self.dispatch.graph.update()
    
    def undo(self):
        self.dispatch.variablesUsed = self.old
        self.dispatch.variablesUsed.sort()
        self.dispatch.regenerateIcons()

#########################################################################################

class LabelChanged(QtGui.QUndoCommand):
    def __init__(self, dispatch, index, description):
        super(self.__class__, self).__init__(description)
        self.dispatch = dispatch
        self.description = description
        
        self.index = index
    
    def redo(self):
        if self.dispatch.controlPanel.displayLabel.isChecked():
            self.dispatch.labelIndex = self.dispatch.controlPanel.labelVariable.currentIndex()
        else:
            self.dispatch.labelIndex = None
        for i in self.dispatch.graph.scene.items():
            i.update()
        self.dispatch.graph.update()
    
    def undo(self):
        pass

#########################################################################################

class LabelCheckBoxChanged(QtGui.QUndoCommand):
    def __init__(self, dispatch, state, description):
        super(self.__class__, self).__init__(description)
        self.dispatch = dispatch
        self.description = description
        
        self.state = state
    
    def redo(self):
        if self.state:
            self.dispatch.labelIndex = self.dispatch.controlPanel.labelVariable.currentIndex()
        else:
            self.dispatch.labelIndex = None
        for i in self.dispatch.graph.scene.items():
            i.update()
        self.dispatch.graph.update()
    
    def undo(self):
        pass

#########################################################################################

class MultipleChanged(QtGui.QUndoCommand):
    def __init__(self, dispatch, old, new, description):
        super(self.__class__, self).__init__(description)
        self.dispatch = dispatch
        self.description = description
        
        self.old = old
        self.new = new
    
    def redo(self):
        self.dispatch.multiple = self.new
        self.dispatch.regenerateIcons()
    
    def undo(self):
        self.dispatch.multiple = self.old
        self.dispatch.regenerateIcons()
    
    def shuffleWithSeed(self, seed):
        self.dispatch.shuffleSeed = seed
        

#########################################################################################

class ShuffleNumberChanged(QtGui.QUndoCommand):
    def __init__(self, dispatch, old, new, description):
        super(self.__class__, self).__init__(description)
        self.dispatch = dispatch
        self.description = description
        
        self.old = old
        self.new = new

    def redo(self):
        self.shuffleWithSeed(self.new)

    def undo(self):
        self.shuffleWithSeed(self.old)
    
    def shuffleWithSeed(self, seed):
        self.dispatch.shuffleSeed = seed
        self.dispatch.regenerateIcons()
        
        #random.seed(self.dispatch.shuffleSeed)
        #shuffled = copy.copy(self.dispatch.variablesUsed) # selected columns
        #random.shuffle(shuffled)
        #for i in self.dispatch.graph.scene.items():
        #    i.updateSelect(shuffled)
        #self.dispatch.graph.update()

#########################################################################################

class Dispatch(QtGui.QMainWindow):
    dispatchList = []
    def __init__(self):
        super(self.__class__, self).__init__()
        
        self.setGeometry(10, 10, 800, 600)
        self.undoStack = QtGui.QUndoStack()
        
        #################################################################################
        
        #self.displayLabel = False
        
        #################################################################################
        
        self.menuFile = self.menuBar().addMenu("&File")
        actionNewDiagram = QtGui.QAction("&New Diagram", self,
            shortcut=QtGui.QKeySequence.New,
            statusTip = "New diagram window",
            triggered=self.newDispatch)
        
        actionOpenData = QtGui.QAction("&Open Dataset...", self,
            statusTip = "Open a dataset",
            triggered=self.openDataset)
        
        actionExportPNG = QtGui.QAction("&Export as PNG...", self,
            statusTip = "Export graph as PNG",
            triggered=self.exportPNG)
        
        actionExit = QtGui.QAction("E&xit", self, 
            shortcut="Ctrl+Q",
            statusTip="Exit the application",
            triggered=QtGui.qApp.closeAllWindows)
        
        self.addActions(self.menuFile, [
            actionNewDiagram, 
            actionOpenData,
            actionExportPNG,
            actionExit
        ])
        
        self.menuEdit = self.menuBar().addMenu("&Edit")
        actionUndo = QtGui.QAction("&Undo", self,
            shortcut=QtGui.QKeySequence.Undo,
            statusTip="Undo last action",
            triggered=self.undoStack.undo)
        
        actionRedo = QtGui.QAction("&Redo", self,
            shortcut=QtGui.QKeySequence.Redo,
            statusTip="Redo last action",
            triggered=self.undoStack.redo)
        
        actionSelectAll = QtGui.QAction("Select &All", self, 
            shortcut="Ctrl+A",
            statusTip = "Select all items", 
            triggered=self.selectAll)
        
        actionDeselectAll = QtGui.QAction("D&eselect All", self, 
            shortcut="Ctrl+D",
            statusTip = "Deselect all items", 
            triggered=self.deselectAll)
        
        self.addActions(self.menuEdit, [actionUndo, actionRedo, actionSelectAll, actionDeselectAll])
        
        #################################################################################
        
        self.graph = GraphWidget(self)
        self.controlPanel = ControlPanel(self)
        
        self.labelIndex = None
        self.variablesUsed = None
        self.shuffleSeed = 0
        self.multiple = 1
        
        self.metadata = {}
        
        self.model = { 
            "fileName": None, 
            "variableNames": None
        }
        
        #################################################################################
        
        dock = QtGui.QDockWidget("Control Panel", self)
        dock.setAllowedAreas(QtCore.Qt.AllDockWidgetAreas)
        dock.setWidget(self.controlPanel)
        #dock.setFloating(True)
        self.addDockWidget(QtCore.Qt.RightDockWidgetArea, dock)
        
        self.setCentralWidget(self.graph)
        
    def addActions(self, menu, actions):
        for action in actions:
            if action is None:
                menu.addSeparator()
            else:
                menu.addAction(action)
    
    def newDispatch(self):
        other = Dispatch()
        Dispatch.dispatchList.append(other)
        other.move(self.x() + 40, self.y() + 40)
        other.show()
    
    def setData(self, data):
        self.data = data
        
        nrows = len(self.data)
        ncols = len(self.data[0])
        
        overrows = range(0, nrows)
        overcols = range(0, ncols)
        
        isString = []
        means = []
        counts = []
        sds = []
        stdmins = []
        
        for val in self.data[0]:
            means.append(0.0)
            counts.append(0.0)
            sds.append(0.0)
            stdmins.append(0.0)
            isString.append(False)
        
        #################################################################################
        
        for i in overrows:
            for j in overcols:
                try:
                    self.data[i][j] = float(self.data[i][j])  # Convert numerics
                    # TODO What about years?
                    means[j] += self.data[i][j] # Calc sums for means
                    counts[j] += 1  # Calc counts
                except:
                    if self.data[i][j] == 'NA': # TODO missing array or dialog
                        self.data[i][j] = None
                    else:
                        isString[j] = True
        
        transformed = copy.deepcopy(self.data)
        
        #################################################################################
        
        for i in overcols:  # Calculate the means
            if not isString[i]:
                means[i] = float(means[i])/float(counts[i])
            else:
                means[i] = None
                counts[i] = None
        
        #################################################################################
        
        for i in overcols: # Calculate the sds
            if not isString[i]:
                tSum = 0.0
                for j in overrows:
                    if transformed[j][i]: # Not missing
                        tSum += math.pow(float(transformed[j][i]) - float(means[i]), 2)
                sds[i] = math.sqrt(float(tSum)/float(counts[i]))
            else:
                sds[i] = None
        
        for i in overcols:
            if not isString[i]:
                for j in overrows:
                    if transformed[j][i]: # Not missing
                        transformed[j][i] = (transformed[j][i]-means[i])/sds[i]
        
        #################################################################################
        
        for i in overcols:
            if not isString[i]:
                stdmins[i] = 0.0
                for j in overrows:
                    if transformed[j][i]: # Not missing
                        if transformed[j][i] < stdmins[i]:
                            stdmins[i] = transformed[j][i]
                #for j in overrows:
                #    if transformed[j][i]: # Not missing
                #        transformed[j][i] = transformed[j][i] + stdmins[i] + 5
            else:
                stdmins[i] = None
        
        #################################################################################
        
        variablesNumeric = []
        for i in overcols:
            if not isString[i]:
                variablesNumeric.append(i)
        
        self.areStrings = isString
        
        #################################################################################
        
        self.metadata['means'] = means
        self.metadata['sds'] = sds
        self.metadata['stdmins'] = stdmins
        self.metadata['isNumeric'] = variablesNumeric
        
        del transformed
        
        x = 0
        for row in self.data:
            tree = Tree(self, row, variablesNumeric, x=x, y=x)
            self.graph.scene.addItem(tree)
            x += 2
        
        self.variablesUsed = copy.copy(variablesNumeric)
    
    def regenerateIcons(self):
        temp = copy.deepcopy(self.variablesUsed)
        for i in range(1, self.multiple):
            tempi = copy.deepcopy(self.variablesUsed)
            for j in tempi:
                temp.append(j)
        random.seed(self.shuffleSeed)
        shuffled = copy.copy(temp) # selected columns
        random.shuffle(shuffled)
        for i in self.graph.scene.items():
            i.updateSelect(shuffled)
        self.graph.update()
        
    
    def variablesUsedChanged(self, items):
        command = VariablesUsedChanged(self, items, description="Variables used changed")
        self.undoStack.push(command)
    
    def labelChanged(self, index):
        command = LabelChanged(self, index,
            description="Display label changed")
        self.undoStack.push(command)
    
    def labelCheckBoxChanged(self, state):
        command = LabelCheckBoxChanged(self, state,
            description="Display label checkbox changed")
        self.undoStack.push(command)
    
    def shuffleNumberChanged(self, old, new):
        command = ShuffleNumberChanged(self, old, new, "Setting one path value")
        self.undoStack.push(command)
    
    def multipleChanged(self, old, new):
        command = MultipleChanged(self, old, new, "Multiply variables by new value")
        self.undoStack.push(command)
    
    def setVariableNames(self, names):
        self.model['variableNames'] = names
        counter = 0
        for i in self.model['variableNames']:
            self.controlPanel.labelVariable.insertItem(counter, str(i))
            #self.controlPanel.variableX.insertItem(counter, str(i))
            #self.controlPanel.variableY.insertItem(counter, str(i))
            if self.areStrings[counter]:
                tVal = 'String'
            else:
                tVal = 'Numeric'
            self.controlPanel.variablesDisplayed.addItem(str(i), tVal)
            counter += 1
        self.controlPanel.variablesDisplayed.selectAll() # just numerics
    
    def exportPNG(self):
        self.deselectAll()
        fileName = QtGui.QFileDialog.getSaveFileName(self)
        #image = QtGui.QImage(500, 500, QtGui.QImage.Format_RGB32)
        #painter = QtGui.QPainter(image);
        #self.graph.render(painter)
        #image.save(fileName)
        #painter.end()
        QtGui.QPixmap.grabWidget(self.graph).save(fileName, "PNG")
    
    def selectAll(self):
        for i in self.graph.scene.items():
            i.setSelected(True)
    
    def deselectAll(self):
        for i in self.graph.scene.selectedItems():
            i.setSelected(False)
    
    def setFileName(self, fileName):
        self.model['fileName'] = str(fileName)
        self.controlPanel.dataFileRead.setText(self.model['fileName'])
    
    def openDataset(self):
        fileName = QtGui.QFileDialog.getOpenFileName(self)
        with open(fileName, 'r') as f:
            self.setFileName(fileName)
            reader = csv.reader(f, delimiter=',')
            head = reader.next()
            data = []
            for row in reader:
                data.append(row)
            self.setData(data)
            self.setVariableNames(head)

#########################################################################################

if __name__ == '__main__':
    import sys
    app = QtGui.QApplication(sys.argv)
    app.setApplicationName("HDTreeV " + __version__)
    dispatch = Dispatch()
    dispatch.show()
    sys.exit(app.exec_())