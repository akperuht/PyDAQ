# -*- coding: utf-8 -*-
"""
Modification of realTimeGraph for simple measurements

@author: Aki Ruhtinas
"""
from PyQt5 import QtWidgets
from PyQt5 import QtCore,QtGui
from pyqtgraph import PlotWidget, plot
import pyqtgraph as pg
import matplotlib.pyplot as plt
import numpy as np
import sys
import time
import multiprocessing as mp
import traceback
import datetime

        
class realTimeGraph(QtWidgets.QMainWindow):
    '''
    Python GUI for fast and efficient real time data plotting
    '''

    def __init__(self, *args, **kwargs):
        '''
        Initialize class

        Parameters
        ----------
        *args : 
        **kwargs : 

        Returns
        -------
        None.

        '''
        super(realTimeGraph, self).__init__(*args, **kwargs)
        self.setStyleSheet("background-color: dimgrey;")
        pg.setConfigOption('background', 'k')
        pg.setConfigOption('foreground', 'w')
        self.exitNow = False
    
    
    def init_UI(self, *args, **kwargs): 
        '''
        Initialize UI

        Parameters
        ----------
        *args : 
        **kwargs : 
            Nchannel: number of used data channels

        Returns
        -------
        None.

        '''
        # Read amount of data channels
        self.Nchannel = kwargs['Nchannel']
        self.Nchannel_plotted = self.Nchannel
        self.selected_channels_plotted = [i for i in range(self.Nchannel)]
        
        # Set data channel names
        self.datalabels = ["Channel " + str(i) for i in range(self.Nchannel)]
        if 'labels' in kwargs:
            self.datalabels = kwargs['labels'] 
        
        self.memory_limit = np.inf
        if 'memory_limit' in kwargs:
            self.memory_limit = kwargs['memory_limit'] 
            
        self.isContinuous = False
        if 'continuous' in kwargs:
            self.isContinuous = kwargs['continuous']
            
        if 'filepath' in kwargs:
            self.filepath = kwargs['filepath']
        else:
            self.filepath = 'c:\\'
            
        if 'Nsamples' in kwargs:
            self.dataNsamples = kwargs['Nsamples']
        else:
            self.dataNsamples = 5000
            
        if 'SampleRate' in kwargs:
            self.dataSampleRate = kwargs['SampleRate']
        else:
            self.dataSampleRate = 50000
            
        if 'Thermometers' in kwargs:
            self.therm_list = kwargs['Thermometers']
        else:
            self.therm_list = ['Dipstick','Ling','Kanada','Noiseless']
        
        self.win = pg.GraphicsLayoutWidget(show=True)
        self.setWindowTitle('realTimeGraph')
        toolboxwidth = 350
        
        # Comboboxes
        self.comboX = QtWidgets.QComboBox(self)
        self.comboY = QtWidgets.QComboBox(self)
        
        self.comboGi = QtWidgets.QComboBox(self)
        self.comboGv = QtWidgets.QComboBox(self)
        self.comboRtherm_multip = QtWidgets.QComboBox(self)
        self.comboThermType = QtWidgets.QComboBox(self)
        
        # Toolbox button
        self.toolbuttonChannelsPlotted = QtWidgets.QToolButton(self)
        
        # Labels
        self.comboXlabel = QtWidgets.QLabel(self)
        self.comboYlabel = QtWidgets.QLabel(self)
        self.comboGilabel = QtWidgets.QLabel(self)
        self.comboGvlabel = QtWidgets.QLabel(self)
        self.comboRtherm_multip_label = QtWidgets.QLabel(self)
        self.comboThermTypeLabel = QtWidgets.QLabel(self)
        self.paramsLabel = QtWidgets.QLabel(self)
        self.pointsLabel = QtWidgets.QLabel(self)
        self.tempLabel = QtWidgets.QLabel(self)
        self.settingsLabel = QtWidgets.QLabel(self)
        self.t_elapsedLabel = QtWidgets.QLabel(self)
        self.freqLabel = QtWidgets.QLabel(self)
        self.scrollNLabel = QtWidgets.QLabel(self)
        self.measParamsLabel = QtWidgets.QLabel(self)
        self.spinNsamplesLabel = QtWidgets.QLabel(self)
        self.spinSampleRateLabel = QtWidgets.QLabel(self)
        self.toolmenuChannelsPlottedLabel = QtWidgets.QLabel(self)
        self.toolmenuChannelsLabel = QtWidgets.QLabel(self)
        
        # PushButton
        self.startButton = QtWidgets.QPushButton(self)
        self.selectFileButton = QtWidgets.QPushButton(self)
        self.clearPlotButton = QtWidgets.QPushButton(self)
        
        # Radiobutton
        self.scrollRadio = QtWidgets.QRadioButton(self)
        self.autosensRadio = QtWidgets.QRadioButton(self)
        
        # Spinbox
        self.scrollNSpin = QtWidgets.QSpinBox(self)
        self.spinNsamples = QtWidgets.QSpinBox(self)
        self.spinSampleRate = QtWidgets.QSpinBox(self)
        
        self.layout1 = QtWidgets.QHBoxLayout()
        self.layout2 = QtWidgets.QVBoxLayout()
        
        self.measParamsFrame = QtWidgets.QFrame()
        self.measParamsFrame.setStyleSheet("background-color: gray;")
        self.measParamsLayout = QtWidgets.QGridLayout(self.measParamsFrame)
        
        self.settingsFrame = QtWidgets.QFrame()
        self.settingsFrame.setStyleSheet("background-color: gray;")
        self.settingsLayout = QtWidgets.QGridLayout(self.settingsFrame)

        self.paramsFrame = QtWidgets.QFrame()
        self.paramsFrame.setStyleSheet("background-color: gray;")
        self.paramsLayout = QtWidgets.QGridLayout(self.paramsFrame)  
        
        self.tempFrame = QtWidgets.QFrame()
        self.tempFrame.setStyleSheet("background-color: gray;")
        self.tempLayout = QtWidgets.QGridLayout(self.tempFrame)
        
        # Add widgets to measParamsLayout
        self.measParamsLayout.addWidget(self.measParamsLabel)
        self.measParamsLayout.setColumnStretch(0, 1)
        
        # Rtherm multip
        i=1
        # Gi
        self.measParamsLayout.addWidget(self.comboGilabel,*(i+1,0))
        self.measParamsLayout.addWidget(self.comboGi,*(i+1,1))
        # Gv
        self.measParamsLayout.addWidget(self.comboGvlabel,*(i,0))
        self.measParamsLayout.addWidget(self.comboGv,*(i,1))
        self.measParamsLayout.addWidget(self.autosensRadio,*(i+2,0)) 
        self.measParamsLayout.addWidget(self.startButton,*(i+3,1))
        
        
        # Add widgets to paramsLayout 
        self.paramsLayout.addWidget(self.paramsLabel,*(0,0),1,3) # Span 3 columns wide
        self.paramsLayout.addWidget(self.t_elapsedLabel,*(1,0),1,3) 
        self.paramsLayout.addWidget(self.freqLabel,*(2,0),1,3)
        self.paramsLayout.addWidget(self.pointsLabel,*(3,0),1,3)     
        self.paramsLayout.addWidget(self.spinNsamples,*(4,2),1,1)
        self.paramsLayout.addWidget(self.spinNsamplesLabel,*(4,0),1,1)
        self.paramsLayout.addWidget(self.spinSampleRate,*(5,2),1,1)
        self.paramsLayout.addWidget(self.spinSampleRateLabel,*(5,0),1,1)
        self.paramsLayout.addWidget(self.selectFileButton,*(7,2),1,1) # Span 1 column wide
        
        # Add widgets to tempFrame
        self.tempLayout.addWidget(self.tempLabel,0,0,1,2)
        self.tempLayout.addWidget(self.comboThermTypeLabel,1,0)
        self.tempLayout.addWidget(self.comboThermType,1,1)
        self.tempLayout.addWidget(self.comboRtherm_multip_label,*(2,0))
        self.tempLayout.addWidget(self.comboRtherm_multip,*(2,1))
        
        # Add XY comboboxes and labels
        self.settingsLayout.addWidget(self.settingsLabel,*(0,0))
        self.settingsLayout.setColumnStretch(0, 1)
        # X
        i=1
        self.settingsLayout.addWidget(self.comboXlabel,*(i+1,0))
        self.settingsLayout.addWidget(self.comboX,*(i+1,1))
        
        # Y
        self.settingsLayout.addWidget(self.comboYlabel,*(i,0))
        self.settingsLayout.addWidget(self.comboY,*(i,1))
        
        # Radiobutton
        self.settingsLayout.addWidget(self.scrollRadio,*(i+2,0)) 
        # Spinbox
        self.settingsLayout.addWidget(self.scrollNSpin,*(i+3,1)) 
        self.settingsLayout.addWidget(self.scrollNLabel,*(i+3,0))
        self.settingsLayout.addWidget(self.toolmenuChannelsPlottedLabel,*(i+4,0))
        self.settingsLayout.addWidget(self.toolbuttonChannelsPlotted,*(i+4,1))
        self.settingsLayout.addWidget(self.clearPlotButton,*(i+5,1))
    
        # Setting Frame size and fixing those
        self.paramsFrame.setSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)
        self.paramsFrame.setFrameStyle(QtWidgets.QFrame.WinPanel | QtWidgets.QFrame.Plain)
        self.settingsFrame.setSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)
        self.settingsFrame.setFrameStyle(QtWidgets.QFrame.WinPanel | QtWidgets.QFrame.Plain)
        self.tempFrame.setSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)
        self.tempFrame.setFrameStyle(QtWidgets.QFrame.WinPanel | QtWidgets.QFrame.Plain)
        self.measParamsFrame.setSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)
        self.measParamsFrame.setFrameStyle(QtWidgets.QFrame.WinPanel | QtWidgets.QFrame.Plain)
        self.paramsFrame.setFixedWidth(toolboxwidth)
        self.settingsFrame.setFixedWidth(toolboxwidth)  
        self.tempFrame.setFixedWidth(toolboxwidth)
        self.measParamsFrame.setFixedWidth(toolboxwidth)
        
        # Add layouts to main layout
        self.layout1.addWidget(self.win)
        self.layout2.addWidget(self.paramsFrame)
        self.layout2.addWidget(self.measParamsFrame)
        self.layout2.addWidget(self.settingsFrame)
        self.layout2.addWidget(self.tempFrame)
        self.layout2.addStretch()
        self.layout1.addLayout(self.layout2)
        
        self.widget = QtWidgets.QWidget()
        
        # Set plot window borders
        self.win.setStyleSheet("QFrame {background-color: white; border:1px solid gray;}")
        
        self.widget.setLayout(self.layout1)
        self.setCentralWidget(self.widget)
        
        
        self.plots=[]
        self.curves=[]
                
        self.mainPlt=None
        self.mainCrv=None
        
        self.mainX=0
        self.mainY=1
        
        # Initialize arrays for data collection
        self.data  = [ [] for y in range(self.Nchannel+1)]
        self.scrollN = 1000
        self.t=[]
        self.Npoint=0
        
        # Attributes for measurement parameters
        self.Gv = 10
        self.Gi = 1e-3
        self.Rtherm_multip = 100
        
        # Create plots and controls
        self.addChannelPlots()
        self.addMainPlot()
        self.addControls()
        self.labelChanged=True
    
        
        # Set event timers
        self.timer=pg.QtCore.QTimer()
        self.timer.timeout.connect(self.updatePlots)
        
        # Set boolean value for m
        self.start = False
        
        self.fname=None
        self.fileok = False
    
        
        

    def addControls(self):
        '''
        Add controls to UI

        Returns
        -------
        None.

        '''
        # Items list
        self.combo_list = self.datalabels
        self.combo_Gv_list = [str(i) for i in [1,10,20,50,100,200,500,1000,2000,5000,10000]]
        self.combo_Gi_list = [str(i) for i in [1e-3,1e-4,1e-5,1e-6,1e-7,1e-8,1e-9,1e-10,1e-11]]
        self.combo_Rtherm_multip_list = [str(i) for i in [1,10,100,1000,10000,100000]]
  
        # Set style 
        style = """QComboBox { 
            background-color: gray; 
            color : white; 
            border: 1px solid white; 
            padding :3px;
            selection-color:cyan;
            font-family: Arial;
            font-size:15 pt;
            }"""

        # Set style for buttons
        self.bstyle_start = """QPushButton { 
            background-color: green; 
            color : white; 
            border: 1px solid white; 
            padding :3px
            }"""
        self.bstyle_stop = """QPushButton { 
            background-color: red; 
            color : white; 
            border: 1px solid white; 
            padding :3px
            }"""
        self.bstyle_settingsbutton = """QPushButton { 
            background-color: blue; 
            color : white; 
            border: 1px solid white; 
            padding :3px
            }"""
    
        self.bstyle_toolmenu = """QMenu { 
            background-color: gray; 
            color : white; 
            border: 1px solid white; 
            padding :3px;
            selection-color:cyan;
            font-family: Arial;
            font-size:15 pt;
            }"""
        self.bstyle_toolbutton = """QToolButton { 
            background-color: gray; 
            color : black; 
            border: 1px solid white; 
            padding :3px;
            selection-color:cyan;
            font-family: Arial;
            font-size:15 pt;
            }"""
    
        self.comboX.setStyleSheet(style)
        self.comboY.setStyleSheet(style)
        self.comboGv.setStyleSheet(style)
        self.comboGi.setStyleSheet(style)
        self.comboRtherm_multip.setStyleSheet(style)
        self.comboThermType.setStyleSheet(style)
    
    
        # Configure start button
        self.startButton.setStyleSheet(self.bstyle_start)   
        self.startButton.setText('Start')
        self.startButton.clicked.connect(self.startButtonClicked)
        
        # Configure file selection button
        self.selectFileButton.setStyleSheet(self.bstyle_settingsbutton)   
        self.selectFileButton.setText('Select file')
        self.selectFileButton.clicked.connect(self.selectFileButtonClicked)
        
        # Configure plot clear button
        self.clearPlotButton.setStyleSheet(self.bstyle_settingsbutton)
        self.clearPlotButton.setText('Clear Plot')
        self.clearPlotButton.clicked.connect(self.clearPlot)
    

        # Toolbutton to choose channels to plot
        self.toolbuttonChannelsPlotted.setText('Channels    ')
        self.toolbuttonChannelsPlotted.setStyleSheet(self.bstyle_toolbutton)
        self.toolmenuChannelsPlotted = myMenu(self)
        self.toolmenuChannelsPlotted.setStyleSheet(self.bstyle_toolmenu)
        self.toolbuttonChannelsPlotted.setMenu(self.toolmenuChannelsPlotted)
        # Add different channels to toolbutton
        self.actionChsp = []
        for i in range(1,self.Nchannel):
            self.actionChsp.append(self.toolmenuChannelsPlotted.addAction(self.datalabels[i]))
            self.actionChsp[i-1].setCheckable(True)
            self.actionChsp[i-1].checked = True
        self.toolbuttonChannelsPlotted.setPopupMode(QtWidgets.QToolButton.MenuButtonPopup)
        self.toolmenuChannelsPlotted.aboutToHide.connect(self.channelMenuPlottedClicked)
        

        # Adding list of items to combo box 
        self.comboX.addItems(self.combo_list) 
        self.comboY.addItems(self.combo_list)
        self.comboGv.addItems(self.combo_Gv_list) 
        self.comboGi.addItems(self.combo_Gi_list)
        self.comboRtherm_multip.addItems(self.combo_Rtherm_multip_list)
        self.comboThermType.addItems(self.therm_list)
        
        # Selecting default plotting indexes
        self.comboX.setCurrentIndex(0)
        self.comboY.setCurrentIndex(1)
        
        self.comboGv.setCurrentIndex(4)
        self.comboGi.setCurrentIndex(1)
        self.comboRtherm_multip.setCurrentIndex(3)
        self.comboThermType.setCurrentIndex(0)
  
        # adding action to combo boxes 
        self.comboX.activated.connect(self.axisComboChanged) 
        self.comboY.activated.connect(self.axisComboChanged)
        
        self.comboGv.activated.connect(self.measComboChanged)
        self.comboGi.activated.connect(self.measComboChanged)
        self.comboRtherm_multip.activated.connect(self.measComboChanged)
        
        self.comboThermType.activated.connect(self.thermComboChanged)

        # Setting for labels       
        #self.comboXlabel.setFrameStyle(QtWidgets.QFrame.Panel | QtWidgets.QFrame.Sunken)

        labels = [self.comboXlabel,
                  self.comboYlabel,
                  self.paramsLabel,
                  self.pointsLabel,
                  self.tempLabel,
                  self.settingsLabel,
                  self.t_elapsedLabel,
                  self.freqLabel,
                  self.measParamsLabel,
                  self.comboGilabel,
                  self.comboGvlabel,
                  self.comboRtherm_multip_label,
                  self.spinNsamplesLabel,
                  self.spinSampleRateLabel,
                  self.toolmenuChannelsPlottedLabel,
                  self.scrollNLabel,
                  self.comboThermTypeLabel
                  ]
        
        texts=['X axis data ',
               'Y axis data ',
               'Data collection',
               'Number of points: ',
               'Temperature: ',
               'Plot settings',
               'Time elapsed: ',
               'Sampling frequency: ',
               'Measurement',
               'Current gain (Gi) ',
               'Voltage gain (Gv) ',
               'Thermometer multiplier',
               'Samples/point',
               'Sample rate',
               'Visible channels',
               'Window size',
               'Thermometer calibration'
               ]
        j=0
        for l in labels:
            l.setStyleSheet('QLabel {color: white;}')
            l.setAlignment(QtCore.Qt.AlignLeft)
            l.setText(texts[j])
            l.adjustSize()
            l.setFont(QtGui.QFont('Arial', 10))
            l.setLineWidth(2)
            l.setMargin(3)
            if j in [3,6,7]:
                l.setFrameStyle(QtWidgets.QFrame.Panel| QtWidgets.QFrame.Sunken)
            if j in [16]:
                l.setFont(QtGui.QFont('Arial', 8))
            j+=1
        # Label settings
       
        self.settingsLabel.setStyleSheet('QLabel {color: black;}')
        self.settingsLabel.setFont(QtGui.QFont('Arial', 12,weight=QtGui.QFont.Bold))
        self.settingsLabel.setFrameStyle(QtWidgets.QFrame.NoFrame)
        self.paramsLabel.setStyleSheet('QLabel {color: black;}')
        self.paramsLabel.setFont(QtGui.QFont('Arial', 12,weight=QtGui.QFont.Bold))
        self.paramsLabel.setFrameStyle(QtWidgets.QFrame.NoFrame)
        self.tempLabel.setFont(QtGui.QFont('Arial', 12))
        self.measParamsLabel.setStyleSheet('QLabel {color: black;}')
        self.measParamsLabel.setFont(QtGui.QFont('Arial', 12,weight=QtGui.QFont.Bold))
            
        # Radiobutton
        self.scrollRadio.setText('Rolling plot')
        self.scrollRadio.setFont(QtGui.QFont('Arial', 10))
        self.scrollRadio.setStyleSheet('QRadioButton {color: white;}')
        self.scrollRadio.setChecked(False)
        self.scrollRadio.toggled.connect(self.radioClicked)
        
        self.autosensRadio.setText('Auto sensitivity')
        self.autosensRadio.setFont(QtGui.QFont('Arial', 10))
        self.autosensRadio.setStyleSheet('QRadioButton {color: white;}')
        self.autosensRadio.setChecked(False)
        self.autosensRadio.toggled.connect(self.autosensClicked)
        
        self.scrollNLabel.setStyleSheet('QLabel {color: dimgray;}')
        
        # Spinbox 
        self.scrollNSpin.setReadOnly(True)
        self.scrollNSpin.setRange(0,10000)
        self.scrollNSpin.setValue(self.scrollN)
        self.scrollNSpin.setSingleStep(100)
        self.scrollNSpin.valueChanged.connect(self.spinvalueChange)
        
        self.spinNsamples.setRange(1,10000000)
        self.spinNsamples.setValue(self.dataNsamples)
        self.spinNsamples.setSingleStep(100)
        self.spinNsamples.valueChanged.connect(self.spinNsamplesChanged)
        
        self.spinSampleRate.setRange(10,1000000)
        self.spinSampleRate.setValue(int(self.dataSampleRate))
        self.spinSampleRate.setSingleStep(1000)
        self.spinSampleRate.valueChanged.connect(self.spinSampleRateChanged)
        
    def checkFile(self):
        '''
        Function for checking if filepath is selected for saving.
        Also clears the file contents

        Returns
        -------
        None.

        '''
        # Check that file is already specified and if not, show error message
        self.fileok = False
        print('Checking if file path is set')
        if self.fname==None:
            msg = QtWidgets.QMessageBox()
            msg.setIcon(QtWidgets.QMessageBox.Critical)
            msg.setText("File Error")
            msg.setInformativeText('File path missing: select output file')
            msg.setWindowTitle("File Error")
            msg.exec_()
        else:
            print('File path is ok')
            # Try to clear the file
            try:
                print('Trying to clear the file')
                open(self.fname, 'w').close()
                # Everything ok, set flag to 
                print('Success')
                self.fileok=True
            except Exception as e:
                print(str(e))
                print('File error')
                # Show error message 
                        
    def startButtonClicked(self):
        '''
        Handle event when start button is clicked

        Returns
        -------
        None.

        '''
        if self.start:
            # Change boolean value and give signal to main script
            self.start = False
            self.timer.stop()
            self.qout.put('stop')
            # Change button appearance accordingly
            self.startButton.setText('Start')
            self.startButton.setStyleSheet(self.bstyle_start)
        else:
            # Change boolean value and give signal to main script
            # Get filename if filename is empty or not temporary file
            if self.fname == None or self.fname.split('/')[-1].lower() not in ['temp.data','temp.dat','temp.txt','test.dat','test.data']:
                self.fname = QtWidgets.QFileDialog.getSaveFileName(self, 'Save file', self.filepath,"")[0]
            # Put filename to output Queue
            self.qout.put({'fname':self.fname})
            # Check and initialize file
            self.checkFile()
            if self.fileok:
                self.start = True
                self.timer.start()
                self.qout.put('start')
                # Change button appearance accordingly
                self.startButton.setText('Stop')
                self.startButton.setStyleSheet(self.bstyle_stop)  
                # Signal to main script 

    
    def channelMenuClicked(self):
        '''
        Handler to read selected channels

        Returns
        -------
        None.

        '''
        #self.selected_channels = []
          
    def channelMenuPlottedClicked(self):
        '''
        Handler to changed amount of plotted graphs

        Returns
        -------
        None.

        '''
        self.selected_channels_plotted = []
        # Get channels names for all the selected channels
        i = 1
        for ach in self.actionChsp:
            if ach.isChecked():
                self.selected_channels_plotted.append(i)
            i+=1
        #print(self.selected_channels)
        
        # Remove old channel plots
        for row in range(0,self.Nchannel_plotted):
            item = self.win.getItem(row, 0)
            if item!= None:
                self.win.removeItem(item)
                        
        # Update channel count
        self.Nchannel_plotted = len(self.selected_channels_plotted)
        
        # Reset plots and curves
        self.plots = []
        self.curves = []
        
        # Draw channel plots again
        self.addChannelPlots()
        
        
        
             
    def selectFileButtonClicked(self):
        '''
        Dialog to get filename for data saving

        Returns
        -------
        None.

        '''
        # Make sure that data collection is not running while setting new filename
        if self.start:
            self.startButtonClicked()
        # Get filename
        self.fname = QtWidgets.QFileDialog.getSaveFileName(self, 'Save file', self.filepath,"")[0]
        # Put filename to output Queue
        self.qout.put({'fname':self.fname})
        
        
        
    def spinvalueChange(self):
        '''
        Handler to change scrolling plot window size according to spinbox

        Returns
        -------
        None.

        '''
        self.scrollN = self.scrollNSpin.value()
        
        
    def spinNsamplesChanged(self):
        '''
        Handler for setting samples/point for data collection

        Returns
        -------
        None.

        '''
        self.dataNsamples = self.spinNsamples.value()
        self.qout.put({'Nsamples':self.dataNsamples})
        
        
        
    def spinSampleRateChanged(self):
        '''
        Handler for setting sample rate for data collection

        Returns
        -------
        None.

        '''
        self.dataSampleRate = self.spinSampleRate.value()
        self.qout.put({'SampleRate':self.dataSampleRate})
        
        
    def autosensClicked(self):
        '''
        Handler for event when automatic sensitivity radio button is clicked

        Returns
        -------
        None.

        '''      
        if self.autosensRadio.isChecked():
            self.qout.put({'autosens':True})
            print('AutoSens on')
        else:
            self.qout.put({'autosens':False})
            print('AutoSens off')

    def radioClicked(self):
        '''
        Handler for event when radiobutton is toggled

        Returns
        -------
        None.

        '''
        # ScrollRadio
        if self.scrollRadio.isChecked():
            self.scrollNLabel.setStyleSheet('QLabel {color: white;}')
            self.scrollNSpin.setReadOnly(False)
        else:
            self.scrollNLabel.setStyleSheet('QLabel {color: dimgrey;}')
            self.scrollNSpin.setReadOnly(True)

        
    def setDataQueue(self,dataQueue, dictQueue, qout):
        '''
        Set queue for data handling

        Parameters
        ----------
        dataQueue : multiprocessing.Queue
            
            Queue used to add data to plots
            
        dictQueue : multiprocessing.Queue
            
            Queue used to pass metadata to main UI
            Supported keys:
                "Temperature"
                "Npoints"
            
        Returns
        -------
        None.

        '''
        self.queue = dataQueue
        self.dictqueue = dictQueue
        self.qout = qout
        
    
    def addChannelPlots(self):
        '''
        Adds channel plots to UI

        Returns
        -------
        None.

        '''
        k=0
        j=0
        for i in range(0,self.Nchannel):
            if i not in self.selected_channels_plotted:
                continue
            # Add plot to specific place in the window
            pi = self.win.addPlot(row=k, col=j)
            # Use automatic downsampling and clipping to reduce the drawing load
            pi.setDownsampling(mode='peak')
            # Attempt to draw only points within the visible range of the ViewBox.
            pi.setClipToView(True)
            
            # Set labels for the plots
            self.label_style = {'color': '#EEE', 'font-size': '10pt'}
            pi.setLabel('left', self.datalabels[i], **self.label_style)  
            # Plot graphs
            ci=pi.plot(pen=(i,self.Nchannel), width=3)
            #Set opacity
            ci.setAlpha(0.6, False) 
            
            #Add plots and curves to array for easy handling
            self.plots.append(pi)
            self.curves.append(ci)
            k+=1
            
            
    def addMainPlot(self):
        '''
        Adds main plot to UI

        Returns
        -------
        None.

        '''
        self.mainPlt = self.win.addPlot(row=0, col=2, rowspan=self.Nchannel,colspan=2)
        # Use automatic downsampling and clipping to reduce the drawing load
        self.mainPlt.setDownsampling(mode='peak')
        #self.mainPlt.setClipToView(True)
        
        self.mainlabel_style = {'color': '#EEE', 'font-size': '10pt'}
        self.mainPlt.setLabel('left', "Y", **self.mainlabel_style)
        self.mainPlt.setLabel('bottom', "X", **self.mainlabel_style) 
        
        # Make scatterplot this time
        self.mainCrv=self.mainPlt.plot(pen=None,
              symbol='o',
              symbolPen=pg.mkPen(color=(0, 0, 255), width=0),                                      
              symbolBrush=pg.mkBrush(0, 0, 255, 255),
              symbolSize=7)
        # Set opacity
        self.mainCrv.setAlpha(0.6, False) 
        self.win.setStyleSheet("border : 3px solid white;")
        
    def updatePlots(self):
        '''
        Updates plots with new data

        Returns
        -------
        None.

        '''
        i=0
        try:
            # Extract all the data from queue
            while not self.queue.empty():
                # Extract data from queue
                data_in=self.queue.get_nowait()
                self.Ndata_in = len(data_in) # Get length of incoming data
                if data_in == 'Exit':
                    self.close()
                    sys.exit()
                j=0
                # Add data to data array and check for size limit
                datacount = sys.getsizeof(self.data[0]*len(self.data))
                if datacount > self.memory_limit:
                    for di in data_in:
                        self.data[j].pop(0)
                        self.data[j].append(di)
                        j+=1
                else:
                    for di in data_in:
                        self.data[j].append(di)
                        j+=1
            i=0
            # Add data to channel plots
            # Plot the data
            for ci in self.curves:
                if self.scrollRadio.isChecked():
                    ci.setData(self.data[0][-self.scrollN:],self.data[self.selected_channels_plotted[i]][-self.scrollN:])
                else:
                    ci.setData(self.data[0],self.data[self.selected_channels_plotted[i]])
                self.Npoint+=1
                i+=1
            # Add data to main plot
            if self.scrollRadio.isChecked():
                self.mainCrv.setData(self.data[self.mainX][-self.scrollN:],self.data[self.mainY][-self.scrollN:])
            else:
                self.mainCrv.setData(self.data[self.mainX],self.data[self.mainY])
            
            # Update point count if that is provided via dictQueue
            params={}
            # Extract all the data from queue with try to prevent critical data plotting not to fail
            try:
                while not self.dictqueue.empty():
                    params=self.dictqueue.get_nowait()
                if "Npoints" in params:
                    self.pointsLabel.setText('Number of points: ' + str(params["Npoints"]))
                if "Temperature" in params:
                    T = params["Temperature"]
                    if T<1:
                        self.tempLabel.setText('Temperature: {T:.2f} mK'.format(T=T*1e3))
                    else:
                        self.tempLabel.setText('Temperature: {T:.2f} K'.format(T=T))
                if "Freq" in params:
                    self.freqLabel.setText('Sampling frequency: ' + str(params["Freq"]))
                if len(self.data[0])>1:
                   self.t_elapsedLabel.setText('Time elapsed: ' + str(datetime.timedelta(seconds=int(self.data[0][-1]))))
            except Exception as e:
                traceback.print_exc()
                
            # Update main plot labels if needed
            if self.labelChanged:
                # Update labels
                self.updateMainPlotLabels()
                # Labels updated, change status to False
                self.labelChanged = False
            if self.exitNow:
                sys.exit()
        except Exception as e:
            # Print full traceback for easier debugging
            traceback.print_exc()
         
    def clearPlot(self):
        '''
        Method to clear plotting data, does not affect to collected data

        Returns
        -------
        None.

        '''
        self.data = [ [] for y in range(self.Ndata_in)]
        
    
    def changeLabels(self,labels):
        '''
        function to change labels

        Parameters
        ----------
        labels : array(string)
            labels for each channel

        Returns
        -------
        None.

        '''
        i=0
        for pi in self.plots:
            pi.setLabel('left', labels[i], **self.label_style)
        
    def thermComboChanged(self):
        '''
        Handle event when thermometer type is changed

        Returns
        -------
        None.

        '''
        # Get thermometer name
        self.thermometer = self.therm_list[self.comboThermType.currentIndex()]
        # Notify measurement program  for thermometer change
        self.qout.put({"ThermCalibName":self.thermometer})

    def measComboChanged(self,*args):
        '''
        Handle event when combobox is changed

        Parameters
        ----------
        *args : int
            selected index of the combobox. Not in use
        Returns
        -------
        None.

        '''
        self.Gv = self.combo_Gv_list[self.comboGv.currentIndex()]
        self.Gi = self.combo_Gi_list[self.comboGi.currentIndex()]
        self.Rtherm_multip = self.combo_Rtherm_multip_list[self.comboRtherm_multip.currentIndex()]
        self.qout.put({'Gv':self.Gv,'Gi':self.Gi,'Rtherm_multip':self.Rtherm_multip})

    def axisComboChanged(self,*args):
        '''
        Handle event when combobox is changed

        Parameters
        ----------
        *args : int
            selected index of the combobox. Not in use
        Returns
        -------
        None.

        '''
        # Select data to be plotted for X and Y axis
        self.mainX = self.comboX.currentIndex()
        self.mainY = self.comboY.currentIndex()
        # Indicate that labels need to be updated
        self.labelChanged=True

    def updateMainPlotLabels(self):
        '''
        Updates main plot X and Y labels according to what data they are plotting

        Returns
        -------
        None.

        '''
        # X label
        self.mainPlt.setLabel('bottom', self.combo_list[self.mainX], **self.mainlabel_style)
        self.mainPlt.setLabel('left', self.combo_list[self.mainY], **self.mainlabel_style)
        
    def Run(self):
        # Start updating the plot
        self.timer.start(25)
        


class myMenu(QtWidgets.QMenu):
    '''
    Modified menu to keep it open
    '''
    def actionEvent(self, event):
        super().actionEvent(event)
        self.show()
        
        
def main(q1,q2,qin):
    app = QtWidgets.QApplication(sys.argv)
    app.setStyle("fusion")
    main = realTimeGraph()
    main.init_UI(Nchannel=6,continuous=False,memory_limit=5000000)
    main.setDataQueue(q1,q2,qin)
    main.Run()
    main.show()
    sys.exit(app.exec_())

def addData(q1,q2,pipe):
    '''
    Function to generate random data to test the data passing to the realTimeGraph

    '''
    t0=time.perf_counter()
    N=0
    Nmax=1251
    while True:
        t1=time.perf_counter()
        data_out=[t1-t0]
        for i in range(5):
            data_out.append(np.random.rand(1)[0]*i)
        T=np.around((21+np.random.rand(1)[0])*1e-2,decimals=5)
        q1.put(data_out)
        q2.put({"Npoints" : N, "Temperature": T, "Progress": np.ceil(N/Nmax*1000)})
        N+=1
        time.sleep(0.01)
        
if __name__ == '__main__':
    q1 = mp.Queue()
    q2 = mp.Queue()
    qin = mp.Queue()
    worker = mp.Process(target=addData, args=(q1,q2,qin))
    worker.start()
    main(q1,q2,qin)
    
        
        
        
