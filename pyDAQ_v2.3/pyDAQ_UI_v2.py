# -*- coding: utf-8 -*-
"""
Modification of realTimeGraph for simple measurements

@author: Aki Ruhtinas
"""
from PySide6 import QtWidgets
from PySide6 import QtCore,QtGui
from pyqtgraph import PlotWidget, plot
import pyqtgraph as pg
import matplotlib.pyplot as plt
import matplotlib as mpl
import numpy as np
import sys
import time
import multiprocessing as mp
import traceback
import datetime
import yaml
from functools import partial
import json
import uuid
import pyvisa

        
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
        # Main background color
        self.setStyleSheet("background-color: rgb(25, 35, 45);")
        pg.setConfigOption('background', (15, 20, 30))
        pg.setConfigOption('foreground', (230, 238, 255))
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
        self.available_channels = ['Dev1/ai'+str(i) for i in range(16)]
        self.Nchannel = len(self.available_channels)
        if 'Nchannel' in kwargs:
            self.Nchannel = kwargs['Nchannel']   
        self.Nchannel_plotted = self.Nchannel
        
        # Initialize uuid
        self.uuid = 0
        
        self.disable_plotting = False
        if 'disable_plotting' in kwargs:
            self.disable_plotting = kwargs['disable_plotting']
        
        self.selected_channels_plotted = [i for i in range(self.Nchannel)]
        
        # Set data channel names
        self.datalabels=[]
        self.datalabels.append('Time (s)')
        for chi in self.available_channels:
            self.datalabels.append(chi)
        if 'labels' in kwargs:
            self.datalabels = kwargs['labels'] 
        
        self.memory_limit = 1000000
        if 'memory_limit' in kwargs:
            self.memory_limit = kwargs['memory_limit']
            print(f'Memory limit:{self.memory_limit}')
            
        if 'rawdataout' in kwargs:
            self.rawdataout = kwargs['rawdataout']
            print(f'Raw data logged:{self.rawdataout}')
            
        self.isContinuous = False
        if 'continuous' in kwargs:
            self.isContinuous = kwargs['continuous']
            
        if 'filepath' in kwargs:
            self.filepath = kwargs['filepath']
        else:
            self.filepath = 'c:\\'
            
        #!!!
        self.available_devices = {'AVS-47':'avs47_params.json',
                                  'Ithaco 1211':'ithaco1211_params.json',
                                  'Ithaco 1201':'ithaco1201_params.json'
                                  }
        if 'available_devices' in kwargs:
            self.available_devices = kwargs['available_devices']
            
        if 'Nsamples' in kwargs:
            self.dataNsamples = kwargs['Nsamples']
        else:
            self.dataNsamples = 5000
            
        if 'SampleRate' in kwargs:
            self.dataSampleRate = kwargs['SampleRate']
        else:
            self.dataSampleRate = 50000
            
        if 'Nlogging' in kwargs:
            self.N_logging = kwargs['Nlogging']
        else:
            self.N_logging = 10
            
        if 'Thermometers' in kwargs:
            self.therm_list = kwargs['Thermometers']
        else:
            self.therm_list = ['None','Dipstick','Morso','Ling','Kanada','Noiseless']
            
        if 'advanced_mode' in kwargs:
            self.advanced_mode = kwargs['advanced_mode']
        else:
            self.advanced_mode = False
        
        if 'available_channels' in kwargs:
            self.available_channels = kwargs['available_channels']          
        
        self.win = pg.GraphicsLayoutWidget(show=True)
        self.setWindowTitle('realTimeGraph')

        
        self.createWidgets()
        
        self.widget = QtWidgets.QWidget()
        
        # Set plot window borders
        self.win.setStyleSheet("""
                               QFrame {
            background-color: white; 
            border:3px solid rgb(166, 166, 166);
            border-radius: 5px;
            }""")
        
        self.widget.setLayout(self.layout1)
        self.setCentralWidget(self.widget)
        
        self.Npoints_total = 0
        
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
        
        
        self.selected_channels_measured_index = [0,1,2]
        self.selected_channels_measured = ['Dev1/ai0','Dev1/ai1','Dev1/ai2']
        
        self.outputDataViewLabels = []
        self.rawDataViewLabels = []
    
        
    def createWidgets(self):
        '''
        Function to create all the necessary widgets

        Returns
        -------
        None.

        '''
        
        toolboxwidth = 300
        
        self.panel_color = 'rgb(57, 68, 79)'
        
        # Comboboxes
        self.comboX = QtWidgets.QComboBox(self)
        self.comboY = QtWidgets.QComboBox(self)
        
        self.comboRtherm_multip = QtWidgets.QComboBox(self)
        self.comboThermType = QtWidgets.QComboBox(self)
        self.comboThermCh = QtWidgets.QComboBox(self)
        
        # Toolbox button
        self.toolbuttonChannelsPlotted = QtWidgets.QToolButton(self)
        self.toolbuttonChannelsMeasured = QtWidgets.QToolButton(self)
        
        # Labels
        self.comboXlabel = QtWidgets.QLabel(self)
        self.comboYlabel = QtWidgets.QLabel(self)
        self.comboRtherm_multip_label = QtWidgets.QLabel(self)
        self.comboThermTypeLabel = QtWidgets.QLabel(self)
        self.comboThermChLabel = QtWidgets.QLabel(self)
        self.spinNlogginglabel = QtWidgets.QLabel(self)
        self.paramsLabel = QtWidgets.QLabel(self)
        self.pointsLabel = QtWidgets.QLabel(self)
        self.dataviewLabel = QtWidgets.QLabel(self)
        self.settingsLabel = QtWidgets.QLabel(self)
        self.t_elapsedLabel = QtWidgets.QLabel(self)
        self.freqLabel = QtWidgets.QLabel(self)
        self.scrollNLabel = QtWidgets.QLabel(self)
        self.measParamsLabel = QtWidgets.QLabel(self)
        self.spinNsamplesLabel = QtWidgets.QLabel(self)
        self.spinSampleRateLabel = QtWidgets.QLabel(self)
        self.toolmenuChannelsPlottedLabel = QtWidgets.QLabel(self)
        self.toolmenuChannelsMeasuredLabel = QtWidgets.QLabel(self)
        self.channelParamsLabel = QtWidgets.QLabel(self)
        self.thermometerLabel = QtWidgets.QLabel(self)
        
        # PushButton
        self.startButton = QtWidgets.QPushButton(self)
        self.selectFileButton = QtWidgets.QPushButton(self)
        self.clearPlotButton = QtWidgets.QPushButton(self)
        
        # Radiobutton
        self.scrollRadio = QtWidgets.QRadioButton(self)
        
        # Spinbox
        self.scrollNSpin = QtWidgets.QSpinBox(self)
        self.spinNsamples = QtWidgets.QSpinBox(self)
        self.spinSampleRate = QtWidgets.QSpinBox(self)
        self.spinNlogging = QtWidgets.QSpinBox(self)
        
        self.layout1 = QtWidgets.QHBoxLayout()
        self.layout2 = QtWidgets.QVBoxLayout()
        self.layout3 = QtWidgets.QVBoxLayout()
        
        self.measParamsFrame = QtWidgets.QFrame()
        self.measParamsFrame.setStyleSheet(f"background-color: {self.panel_color};")
        self.measParamsLayout = QtWidgets.QGridLayout(self.measParamsFrame)
        
        self.channelParamsFrame = QtWidgets.QFrame()
        self.channelParamsFrame.setStyleSheet(f"background-color: {self.panel_color};")
        self.channelParamsLayout = QtWidgets.QGridLayout(self.channelParamsFrame)
        
        self.settingsFrame = QtWidgets.QFrame()
        self.settingsFrame.setStyleSheet(f"background-color: {self.panel_color};")
        self.settingsLayout = QtWidgets.QGridLayout(self.settingsFrame)

        self.paramsFrame = QtWidgets.QFrame()
        self.paramsFrame.setStyleSheet(f"background-color: {self.panel_color};")
        self.paramsLayout = QtWidgets.QGridLayout(self.paramsFrame)  
        
        self.dataviewFrame = QtWidgets.QFrame()
        self.dataviewFrame.setStyleSheet(f"background-color: {self.panel_color};")
        self.dataviewLayout = QtWidgets.QGridLayout(self.dataviewFrame)
        #self.measParamsLayout.addWidget(self.selectFileButton,1,0,1,1)
        
        # Add widgets to paramsLayout 
        self.paramsLayout.addWidget(self.paramsLabel,*(0,0),1,3) # Span 3 columns wide
        self.paramsLayout.addWidget(self.t_elapsedLabel,*(1,0),1,3) 
        self.paramsLayout.addWidget(self.freqLabel,*(2,0),1,3)
        self.paramsLayout.addWidget(self.pointsLabel,*(3,0),1,3)     
        self.paramsLayout.addWidget(self.spinNsamples,*(4,2),1,1)
        self.paramsLayout.addWidget(self.spinNsamplesLabel,*(4,0),1,1)
        self.paramsLayout.addWidget(self.spinSampleRate,*(5,2),1,1)
        self.paramsLayout.addWidget(self.spinSampleRateLabel,*(5,0),1,1)
        self.paramsLayout.addWidget(self.spinNlogginglabel,*(6,0),1,1)
        self.paramsLayout.addWidget(self.spinNlogging,*(6,2),1,1)
        self.paramsLayout.addWidget(self.toolmenuChannelsMeasuredLabel,*(7,0),1,1)
        self.paramsLayout.addWidget(self.toolbuttonChannelsMeasured,*(7,2),1,1)
        self.paramsLayout.addWidget(self.startButton,*(8,2),1,1)
        
        
        # Add widgets to channelParamsLayout
        self.channelParamsLayout.addWidget(self.channelParamsLabel,*(1,0),1,1)
        #self.paramsLayout.addWidget(self.selectFileButton,*(7,2),1,1) # Span 1 column wide
        
        # Add widgets to tempFrame
        self.dataviewLayout.addWidget(self.thermometerLabel, 0,0,1,3)
        self.dataviewLayout.addWidget(self.comboThermChLabel,*(2,0))
        self.dataviewLayout.addWidget(self.comboThermCh,*(2,2))
        self.dataviewLayout.addWidget(self.comboThermTypeLabel,3,0)
        self.dataviewLayout.addWidget(self.comboThermType,3,2)        
        self.dataviewLayout.addWidget(self.dataviewLabel,5,0,1,3)
        
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
        self.dataviewFrame.setSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)
        self.dataviewFrame.setFrameStyle(QtWidgets.QFrame.WinPanel | QtWidgets.QFrame.Plain)
        self.channelParamsFrame.setSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)
        self.channelParamsFrame.setFrameStyle(QtWidgets.QFrame.WinPanel | QtWidgets.QFrame.Plain)
        self.paramsFrame.setFixedWidth(toolboxwidth)
        self.settingsFrame.setFixedWidth(toolboxwidth)
        self.dataviewFrame.setFixedWidth(toolboxwidth)
        self.measParamsFrame.setFixedWidth(toolboxwidth)
        self.channelParamsFrame.setFixedWidth(toolboxwidth)
        
        # Add layouts to main layout
        self.layout1.addWidget(self.win)
        self.layout2.addWidget(self.paramsFrame)
        self.layout2.addWidget(self.settingsFrame)

        self.layout3.addWidget(self.channelParamsFrame)
        self.layout3.addWidget(self.dataviewFrame)
        
        self.layout3.addStretch()
        self.layout2.addStretch()
        
        self.layout1.addLayout(self.layout2)
        self.layout1.addLayout(self.layout3)
        

    def addControls(self):
        '''
        Add controls to UI

        Returns
        -------
        None.

        '''
        # Items list
        self.combo_list = self.datalabels[:4]
        self.combo_Gv_list = [str(i) for i in [1,10,20,50,100,200,500,1000,2000,5000,10000]]
        self.combo_Gi_list = [str(i) for i in [1e-3,1e-4,1e-5,1e-6,1e-7,1e-8,1e-9,1e-10,1e-11]]
        self.combo_Rtherm_multip_list = [str(i) for i in [1,10,100,1000,10000,100000]]
        self.comboThermCh_list = self.available_channels
  
        # Set style 
        self.style = """QComboBox { 
            background-color: rgb(43, 61, 79);
            selection-background-color: gray; 
            color : white; 
            border: 1px solid black; 
            padding :4px;
            selection-color:cyan;
            font-family: Arial;
            font-size:15 pt;
            }
            QComboBox::hover {
            background-color: rgb(55, 79, 102);
                }
            QListView{
            background-color: rgb(57, 68, 79);
            border: 1px solid black; 
            }
                """

        # Set style for buttons
        self.bstyle_start = """QPushButton { 
            background-color: rgb(0, 204, 68);
            color : black;
            border-radius: 3px;
            border: 2px solid black; 
            padding :3px;
            font-weight: bold;
            }
              QPushButton::hover{ 
                  background-color: rgb(0, 230, 77); 
            }
              QPushButton::pressed{ 
                  background-color: rgb(0, 179, 60); 
                }
            """
        self.bstyle_stop = """QPushButton { 
            background-color: rgb(255, 51, 0); 
            color : black;
            border-radius: 3px;
            border: 2px solid black; 
            padding :3px;
            font-weight: bold;
            }
              QPushButton::hover{ 
                  background-color: rgb(255, 71, 26); 
            }
              QPushButton::pressed{ 
                  background-color: rgb(230, 46, 0); 
                }
            """
                
        self.bstyle_settingsbutton = """QPushButton { 
            background-color: rgb(54, 77, 99); 
            color : white;
            border-radius: 3px;
            border: 1px solid black; 
            padding :3px
            }
              QPushButton::hover{ 
                  background-color: rgb(45, 89, 134); 
            }
              QPushButton::pressed{ 
                  background-color: rgb(19, 38, 57); 
                }
            """
    
        self.bstyle_toolmenu = """QMenu { 
            background-color: rgb(128, 128, 128); 
            color : black; 
            border: 1px solid white; 
            padding :3px;
            selection-color:cyan;
            font-family: Arial;
            font-size:15 pt;
            }
            QMenu::selected{
            background-color: rgb(115, 115, 115); 
                }"""
            
        # Create style for tool button
        self.bstyle_toolbutton = """QToolButton { 
            background-color: rgb(43, 61, 79); 
            color : white; 
            border: 1px solid black; 
            padding :3px;
            selection-color:cyan;
            font-family: Arial;
            font-size:15 pt;
            }
            QToolButton::hover {
            background-color: rgb(55, 79, 102);
                }"""
        
        self.spinbox_style = """QSpinBox { 
            background-color: rgb(25, 35, 45); 
            color : white;
            }
            """
    
        # Set up comboboxes
        self.setupComboXY()
        self.comboRtherm_multip.setStyleSheet(self.style)
        self.comboThermType.setStyleSheet(self.style)
        self.comboThermCh.setStyleSheet(self.style)
    
    
        # Configure start button
        self.startButton.setStyleSheet(self.bstyle_start)   
        self.startButton.setText('Start')
        self.startButton.clicked.connect(self.startButtonClicked)
        self.startButton.setFont(QtGui.QFont('Calibri', 12))
                
        # Configure plot clear button
        self.clearPlotButton.setStyleSheet(self.bstyle_settingsbutton)
        self.clearPlotButton.setText('Clear Plot')
        self.clearPlotButton.clicked.connect(self.clearPlot)
    
        # Create channel selectors
        self.createChannelSelector('measured')
        self.createChannelSelector('plotted')
  

        # Adding list of items to combo box 
        self.comboRtherm_multip.addItems(self.combo_Rtherm_multip_list)
        self.comboThermType.addItems(self.therm_list)
        self.comboThermCh.addItems(self.comboThermCh_list)
        
        # Selecting default plotting indexes      
        self.comboRtherm_multip.setCurrentIndex(3)
        #self.comboThermType.setCurrentIndex(0)
        #self.comboThermCh.setCurrentIndex(0)
  
        # adding action to combo boxes 
        self.comboX.activated.connect(self.axisComboChanged) 
        self.comboY.activated.connect(self.axisComboChanged)
        
        self.comboRtherm_multip.activated.connect(self.measComboChanged)
        
        self.comboThermType.activated.connect(self.thermComboChanged)
        self.comboThermCh.activated.connect(self.thermChannelChanged)

        # Setting for labels       

        labels = [self.comboXlabel,
                  self.comboYlabel,
                  self.paramsLabel,
                  self.pointsLabel,
                  self.dataviewLabel,
                  self.settingsLabel,
                  self.t_elapsedLabel,
                  self.freqLabel,
                  self.measParamsLabel,
                  self.spinNlogginglabel,
                  self.comboRtherm_multip_label,
                  self.spinNsamplesLabel,
                  self.spinSampleRateLabel,
                  self.toolmenuChannelsPlottedLabel,
                  self.scrollNLabel,
                  self.comboThermTypeLabel,
                  self.toolmenuChannelsMeasuredLabel,
                  self.comboThermChLabel,
                  self.thermometerLabel,
                  self.channelParamsLabel
                  ]
        
        texts=['X axis data ',
               'Y axis data ',
               'Data collection',
               'Number of points: ',
               'Data output',
               'Plot settings',
               'Time elapsed: ',
               'Sampling frequency: ',
               'Measurement',
               'Requests/logging',
               'Multiplier',
               'Samples/DAQ request',
               'Sample rate',
               'Visible channels',
               'Window size',
               'Calibration',
               'Channels to measure',
               'Channel',
               'Thermometer',
               'Channel settings'
               ]
        
        # Big font size
        self.bigfs = 16
        
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
            if j in [10,15,17]:
                l.setFont(QtGui.QFont('Arial', 10))
            if j in [4]:
                l.setStyleSheet('QLabel {color: black;padding-bottom: 10px;}')
                l.setFont(QtGui.QFont('Arial', self.bigfs,weight=QtGui.QFont.Bold))
            j+=1
            
        # Label settings       
        self.settingsLabel.setStyleSheet('QLabel {color: black;padding-bottom: 10px;}')
        self.settingsLabel.setFont(QtGui.QFont('Arial', self.bigfs,weight=QtGui.QFont.Bold))
        self.settingsLabel.setFrameStyle(QtWidgets.QFrame.NoFrame)
        self.paramsLabel.setStyleSheet('QLabel {color: black;padding-bottom: 10px;}')
        self.paramsLabel.setFont(QtGui.QFont('Arial', self.bigfs,weight=QtGui.QFont.Bold))
        self.paramsLabel.setFrameStyle(QtWidgets.QFrame.NoFrame)
        self.measParamsLabel.setStyleSheet('QLabel {color: black;padding-bottom: 10px;}')
        self.measParamsLabel.setFont(QtGui.QFont('Arial', self.bigfs,weight=QtGui.QFont.Bold))
        self.thermometerLabel.setStyleSheet('QLabel {color: black;padding-bottom: 10px;}')
        self.thermometerLabel.setFont(QtGui.QFont('Arial', self.bigfs,weight=QtGui.QFont.Bold))
        self.channelParamsLabel.setStyleSheet('QLabel {color: black;padding-bottom: 10px;}')
        self.channelParamsLabel.setFont(QtGui.QFont('Arial', self.bigfs,weight=QtGui.QFont.Bold))
            
        
        # Radiobutton
        self.scrollRadio.setText('Rolling plot')
        self.scrollRadio.setFont(QtGui.QFont('Arial', 10))
        self.scrollRadio.setStyleSheet('QRadioButton {color: white;}')
        self.scrollRadio.setChecked(False)
        self.scrollRadio.toggled.connect(self.radioClicked)
        
        self.scrollNLabel.setStyleSheet('QLabel {color: dimgray;}')
        
        # Spinbox 
        self.scrollNSpin.setReadOnly(True)
        self.scrollNSpin.setRange(0,10000)
        self.scrollNSpin.setValue(self.scrollN)
        self.scrollNSpin.setSingleStep(100)
        self.scrollNSpin.valueChanged.connect(self.spinvalueChange)
        self.scrollNSpin.setStyleSheet(self.spinbox_style)
        
        self.spinNsamples.setRange(1,10000000)
        self.spinNsamples.setValue(self.dataNsamples)
        self.spinNsamples.setSingleStep(100)
        self.spinNsamples.valueChanged.connect(self.spinNsamplesChanged)
        self.spinNsamples.setStyleSheet(self.spinbox_style)
        
        self.spinSampleRate.setRange(10,1000000)
        self.spinSampleRate.setValue(int(self.dataSampleRate))
        self.spinSampleRate.setSingleStep(1000)
        self.spinSampleRate.valueChanged.connect(self.spinSampleRateChanged)
        self.spinSampleRate.setStyleSheet(self.spinbox_style)
        
        self.spinNlogging.setRange(1,1000000)
        self.spinNlogging.setValue(int(self.N_logging))
        self.spinNlogging.setSingleStep(10)
        self.spinNlogging.valueChanged.connect(self.spinNloggingRateChanged)
        self.spinNlogging.setStyleSheet(self.spinbox_style)
        
        
        
    def setupComboXY(self):
        '''
        method for setting up Qcomboboxes for main plot X and Y data selection

        Returns
        -------
        None.

        '''
        # Cleat comboboxes
        self.comboX.clear()
        self.comboY.clear()
        # Set stylesheet
        self.comboX.setStyleSheet(self.style)
        self.comboY.setStyleSheet(self.style)
        # Adding list of items to combo box 
        self.comboX.addItems(self.combo_list) 
        self.comboY.addItems(self.combo_list)
        # Selecting default plotting indexes
        self.comboX.setCurrentIndex(0)
        self.comboY.setCurrentIndex(1)
        
        
    def createChannelSelector(self, chtype):
        '''
        Method to create menu for channel selections

        Parameters
        ----------
        chtype : str
            'measured' or 'plotted' depending on which toolbutton to initialize

        Returns
        -------
        None.

        '''
        
        if chtype == 'plotted':
            # Toolbutton to choose channels to plot
            self.toolbuttonChannelsPlotted.setText('Channels    ')
            self.toolbuttonChannelsPlotted.setStyleSheet(self.bstyle_toolbutton)
            self.toolmenuChannelsPlotted = myMenu(self)
            self.toolmenuChannelsPlotted.setStyleSheet(self.bstyle_toolmenu)
            # Add different channels to toolbutton
            self.actionChsp = []
            for i in [0,1,2]:
                self.actionChsp.append(self.toolmenuChannelsPlotted.addAction(self.datalabels[i+1]))
                
            self.toolbuttonChannelsPlotted.setMenu(self.toolmenuChannelsPlotted)
            self.toolbuttonChannelsPlotted.setPopupMode(QtWidgets.QToolButton.MenuButtonPopup)
            self.toolmenuChannelsPlotted.aboutToHide.connect(self.channelMenuPlottedClicked)
   
        elif chtype =='measured':
            # Toolbutton to choose channels to measure
            self.toolbuttonChannelsMeasured.setText('Channels   ')
            self.toolbuttonChannelsMeasured.setStyleSheet(self.bstyle_toolbutton)
            self.toolmenuChannelsMeasured = myMenu(self)
            self.toolmenuChannelsMeasured.setStyleSheet(self.bstyle_toolmenu)
            # Add different channels to toolbutton
            self.actionChsm = []
            for i,di in enumerate(self.available_channels):
                self.actionChsm.append(self.toolmenuChannelsMeasured.addAction(self.available_channels[i]))
                self.actionChsm[i-1].setCheckable(True)
                
            self.actionChsm[0].setChecked(True)
            self.toolbuttonChannelsMeasured.setMenu(self.toolmenuChannelsMeasured)
            self.toolbuttonChannelsMeasured.setPopupMode(QtWidgets.QToolButton.MenuButtonPopup)
            self.toolmenuChannelsMeasured.aboutToHide.connect(self.channelMenuMeasuredClicked)
            
            # Set first 3 channels checked by default
            '''
            self.measCh_checkboxes[0].setChecked(True)
            self.measCh_checkboxes[1].setChecked(True)
            self.measCh_checkboxes[2].setChecked(True)
            '''
        else:
            pass
        
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
        if self.fname==None or self.fname == '':
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
                self.fileok = True
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
        # If already started, stop the program
        if self.start:
            # Change boolean value and give signal to main script
            self.start = False
            self.timer.stop()
            self.qout.put('stop')
            # Change button appearance accordingly
            self.startButton.setText('Start')
            self.startButton.setStyleSheet(self.bstyle_start)
            
        # Start the program
        else:          
            # initialize data array
            self.data  = [ [] for y in range(self.Nchannel+1)]
            # Change boolean value and give signal to main script
            # Get filename if filename is empty or not 'TEMP.DAT'
            #if self.fname == None or self.fname.split('/')[-1].lower() not in ['temp.data','temp.dat','temp.txt']:
            # UPDATE to version 2: get filename no matter what
            self.fname = QtWidgets.QFileDialog.getSaveFileName(self, 'Save file', self.filepath,"")[0]
            
            # Create unique identifier for this measurement
            self.uuid = uuid.uuid4()
                      
            # Open Dialog window to ask metadata
            dg = MetadataDialog(self.selected_channels_measured,self.settingDict,self.available_devices)
            # Write metadata to file
            dg.accepted.connect(self.write_metadata_file)
            dg.rejected.connect(self.metadata_rejected)
            dg.exec_()
                        
            # Check and initialize file
            self.checkFile()
            if self.fileok:
                self.start = True
                self.timer.start()
                # Signal start to main script
                self.qout.put('start')
                # Change button appearance accordingly
                self.startButton.setText('Stop')
                self.startButton.setStyleSheet(self.bstyle_stop)
                
        # Control which widgets are allowed to use
        self.changeVisibility()
        
        # Change total number of points back to zero
        self.Npoints_total = 0

    def metadata_rejected(self):
        # Put filename, UUID and datalabels to output Queue
        self.qout.put({'fname':self.fname,"UUID":self.uuid})

    # Write metadata file
    def write_metadata_file(self, values):
        '''
        Write metadata to YAML file

        Parameters
        ----------
        values : dict
            metadata

        Returns
        -------
        None.

        '''
        # Change data labels based on metadatadialog
        self.datalabels = []
        self.datalabels.append('Time (s)')
        chdict = values['Channel names']
        chnames = []
        chdesc = []
        for ch_name in chdict:
            chdesc.append(chdict[ch_name])
            self.datalabels.append(f'{chdict[ch_name]} ({ch_name})')
        # Update data labels
        self.channelMenuMeasuredClicked(False)
        
        # Put filename, UUID and datalabels to output Queue
        self.qout.put({'fname':self.fname,"UUID":self.uuid,"datalabels":['#Time(s)'] + chdesc + chnames})
        
        # Parse all metadata to one dictionary
        if self.rawdataout:
            dt = {'UUID':str(self.uuid),
                  'Date' :'{0}.{1}.{2}'.format(values['Date'].day(), values['Date'].month(), values['Date'].year()),
                  'Time' : datetime.datetime.now().strftime('%H.%M'),
                  'Sample':values['Sample'],
                  'Author':values['Author'],
                  'Measurement description': values['Description'],
                  'Datafile format':f'Time(s) + Processed data channels ({len(chdict)}) + raw data channels ({len(chdict)})',
                  'Channel names': chdict,
                  'Settings':self.settingDict
                  }
        else:
            dt = {'UUID':str(self.uuid),
                  'Date' :'{0}.{1}.{2}'.format(values['Date'].day(), values['Date'].month(), values['Date'].year()),
                  'Time' : datetime.datetime.now().strftime('%H.%M'),
                  'Sample':values['Sample'],
                  'Author':values['Author'],
                  'Measurement description': values['Description'],
                  'Datafile format':f'Time(s) + Processed data channels ({len(chdict)})',
                  'Channel names': chdict,
                  'Settings':self.settingDict
                  }  
        # Write same filename as measurement name
        fname = self.fname + '.yaml'
        # Writing the data to a YAML file
        with open(fname, 'w') as file:
            yaml.dump(dt, file, sort_keys=False)
        
        
    
    def changeVisibility(self):
        '''
        Method to enable/disable different widgets depending on whether or not the program is running

        Returns
        -------
        None.

        '''
        # Disable controls
        if self.start:
            self.toolbuttonChannelsMeasured.setEnabled(False)
            if not self.advanced_mode:
                self.comboThermType.setEnabled(False)
                self.spinSampleRate.setEnabled(False)
                self.spinNsamples.setEnabled(False)
                self.comboThermCh.setEnabled(False)
        # Enable controls
        else:
            self.spinSampleRate.setEnabled(True)
            self.toolbuttonChannelsMeasured.setEnabled(True)
            self.comboThermType.setEnabled(True)
            self.spinSampleRate.setEnabled(True)
            self.spinNsamples.setEnabled(True)
            self.comboThermCh.setEnabled(True)
                
          

        
    def channelMenuMeasuredClicked(self,update_ch_sett=True):
        '''
        Handler to select which of the available channels are measured

        Returns
        -------
        None.

        '''
        self.selected_channels_measured_index = []
        self.selected_channels_measured = []
        
        # Get channels names for all the selected channels
        for i,measchb in enumerate(self.actionChsm):
            if measchb.isChecked():
                self.selected_channels_measured.append(measchb.text())
                self.selected_channels_measured_index.append(i)
                
        self.Nchannel = len(self.selected_channels_measured)
            
        # Communicate measured channels to measurement program
        self.qout.put({'measChannels':self.selected_channels_measured})
        self.qout.put({'measChannelsIndices':self.selected_channels_measured_index})
        
        # Initialize data
        self.data = [ [] for y in range(self.Nchannel+1)]
        
        # Change combobox lists for mainplot
        self.combo_list = ['Time(s)']+[chi for chi in self.selected_channels_measured]
        self.setupComboXY()
        
        self.toolmenuChannelsPlotted.clear()
        # Add different channels to toolbutton
        self.actionChsp = []
        for i,chi in enumerate(self.selected_channels_measured):
            self.actionChsp.append(self.toolmenuChannelsPlotted.addAction(chi))
            self.actionChsp[-1].setCheckable(True)
            self.actionChsp[-1].checked = True
            
        # Clear and set temperature channel combobox
        self.comboThermCh.clear()
        self.comboThermCh.addItems(self.selected_channels_measured)
        
        # Make channel setting tab and dataview tab
        if update_ch_sett:
            self.createChannelSettings()
            self.createDataMonitorLabels()
        
        
        
    def createDataMonitorLabels(self):
        '''
        Function to add data view labels

        Returns
        -------
        None.

        '''
        
        #!!!
        
        # Clear dataview channels from dataView frame
        for i in reversed(range(self.dataviewLayout.count())):
            if i>6:
                self.dataviewLayout.itemAt(i).widget().setParent(None)
        # Clear the label lists
        self.outputDataViewLabels = []
        self.rawDataViewLabels = []
        
        # Set up column labels
        labels=['Channel','Output','Raw']
        for i in range(3):
            columnTitleLabel = QtWidgets.QLabel(self)
            columnTitleLabel.setText(labels[i])
            columnTitleLabel.setStyleSheet('QLabel {color: white;}')
            columnTitleLabel.setFont(QtGui.QFont('Arial', 8))
            columnTitleLabel.setAlignment(QtCore.Qt.AlignCenter)
            self.dataviewLayout.addWidget(columnTitleLabel,*(6,i),1,1)
        
        i=0
        k=0
        for chi in self.selected_channels_measured:
            # Create channel label
            chLabel = QtWidgets.QLabel(self)
            chLabel.setText(chi)
            chLabel.setStyleSheet('QLabel {color: rgb(205, 207, 209);}')
            chLabel.setAlignment(QtCore.Qt.AlignCenter)
            chLabel.adjustSize()
            chLabel.setFont(QtGui.QFont('Arial', 10))
            chLabel.setLineWidth(2)
            chLabel.setMargin(3)
           
            # create data viewlabels
            outLabel = QtWidgets.QLabel(self)
            outLabel.setText('0')
            outLabel.setStyleSheet('QLabel {color: rgb(205, 207, 209);}')
            outLabel.setAlignment(QtCore.Qt.AlignCenter)
            outLabel.adjustSize()
            outLabel.setFont(QtGui.QFont('Arial', 10))
            outLabel.setLineWidth(2)
            outLabel.setMargin(3)
            
            
            rawLabel = QtWidgets.QLabel(self)
            rawLabel.setText('0')
            rawLabel.setStyleSheet('QLabel {color: rgb(205, 207, 209);}')
            rawLabel.setAlignment(QtCore.Qt.AlignCenter)
            rawLabel.adjustSize()
            rawLabel.setFont(QtGui.QFont('Arial', 10))
            rawLabel.setLineWidth(2)
            rawLabel.setMargin(3)
           
           # Create horizontal separator
            hline = QHLine()
             # Add widgets to layout
            self.dataviewLayout.addWidget(hline, 7+i, 0, 1, 3)
            self.dataviewLayout.addWidget(chLabel, 7+i+1, 0, 1, 1)
            self.dataviewLayout.addWidget(outLabel, 7+i+1, 1, 1, 1)
            self.dataviewLayout.addWidget(rawLabel, 7+i+1, 2, 1, 1)
            i+=2
            # Add to arrays to present the data
            self.outputDataViewLabels.append(outLabel)
            self.rawDataViewLabels.append(rawLabel)
            k+=1
        
            
    def createChannelSettings(self):
        '''
        Function to create settings for measured channels

        Returns
        -------
        None.

        '''
        
        # Clear channel params frame
        for i in reversed(range(self.channelParamsLayout.count())): 
            self.channelParamsLayout.itemAt(i).widget().setParent(None)
        
        self.combo_device_list = ['None'] + list(self.available_devices.keys())
        

        channelParamsLabel = QtWidgets.QLabel(self)
        self.channelParamsLayout.addWidget(channelParamsLabel,*(0,0),1,4)
        channelParamsLabel.setText('Channel settings')
        channelParamsLabel.setStyleSheet('QLabel {color: black;padding-bottom: 15px;}')
        channelParamsLabel.setFont(QtGui.QFont('Arial', self.bigfs,weight=QtGui.QFont.Bold))
        
        # Add info labels
        labels=['Channel','Device',' ','Multiplier']
        for i in range(4):
            settingTitleLabel = QtWidgets.QLabel(self)
            settingTitleLabel.setText(labels[i])
            settingTitleLabel.setStyleSheet('QLabel {color: white;}')
            settingTitleLabel.setFont(QtGui.QFont('Arial', 8))
            self.channelParamsLayout.addWidget(settingTitleLabel,*(1,i),1,1)
        
       
        # Initialize dict containing comboxes
        self.ChannelDeviceComboList = {}
        
        # Intialize dict containing push buttons
        self.DeviceSettingButtonList = {}
        
        # Initialize dict containing gain labels
        self.channelGainLabelList = {}
               
        # Initalize settings dictionary
        self.settingDict = {}
        # Add channel setting comboboxes and labels
        i=2
        for chi in self.selected_channels_measured:
            # Create channel label
            chLabel = QtWidgets.QLabel(self)
            chLabel.setText(chi)
            chLabel.setStyleSheet('QLabel {color: rgb(205, 207, 209);}')
            chLabel.setAlignment(QtCore.Qt.AlignCenter)
            chLabel.adjustSize()
            chLabel.setFont(QtGui.QFont('Arial', 10))
            chLabel.setLineWidth(2)
            chLabel.setMargin(3)
            
            # Create comboboxes
            comboDevice = QtWidgets.QComboBox(self)
            comboDevice.addItems(self.combo_device_list)
            comboDevice.setStyleSheet(self.style)
            #comboDevice.activated.connect(partial(self.channelDeviceComboClicked,chi))
            comboDevice.activated.connect(lambda index,chi=chi: self.channelDeviceComboClicked(chi, index))
            
            # Create pushButtons
            deviceSettingsButton = QtWidgets.QPushButton(self)
            # Configure button style 
            deviceSettingsButton.setStyleSheet(self.bstyle_settingsbutton)
            deviceSettingsButton.setText('Settings')
            # Connect to same function but communicate which button is pressed using partial
            deviceSettingsButton.clicked.connect(partial(self.deviceSettingButtonClicked,chi))
            
            # Create channel gain labels
            chGainLabel = QtWidgets.QLabel(self)
            chGainLabel.setText('1')
            self.settingDict[chi] = {'Multiplier':1}
            chGainLabel.setStyleSheet('QLabel {color: rgb(205, 207, 209);}')
            chGainLabel.setFont(QtGui.QFont('Arial', 10))
            chGainLabel.setAlignment(QtCore.Qt.AlignCenter)
            
           # Create horizontal separator
            self.hline = QHLine()
            
             # Add widgets to layout
            self.channelParamsLayout.addWidget(self.hline, i, 0, 1, 4) 
            self.channelParamsLayout.addWidget(chLabel,*(i+1,0),1,1)
            self.channelParamsLayout.addWidget(comboDevice,*(i+1,1),1,1)
            self.channelParamsLayout.addWidget(deviceSettingsButton,*(i+1,2),1,1)
            self.channelParamsLayout.addWidget(chGainLabel,*(i+1,3),1,1)
            
            # Add objects to dict
            self.ChannelDeviceComboList[chi] = comboDevice
            self.DeviceSettingButtonList[chi] = deviceSettingsButton
            self.channelGainLabelList[chi] = chGainLabel
            i+=2
        
        
    def channelDeviceComboClicked(self,channel,index=None):
        '''
        Function to handle changes in channel settings

        Returns
        -------
        None.

        '''
        print(channel)
        
              
    def deviceSettingButtonClicked(self,channel):
        '''
        Function to handle setting button push

        Returns
        -------
        None.

        '''
        if self.ChannelDeviceComboList[channel].currentIndex() == 0:
            devicename = 'None'
        else:
            devices = list(self.available_devices.keys())
            devicename = devices[self.ChannelDeviceComboList[channel].currentIndex()-1]
        if devicename!='None':
            paramsfile = self.available_devices[devicename]
            # Open settings dialog
            dg = DeviceSettingDialog(self.settingDict[channel],paramsfile,channel) #!!! Working here
            # Connect dialog to handler
            dg.accepted.connect(self.handleDeviceSettings)
            dg.exec_()
        
    def handleDeviceSettings(self,settings):
        '''
        Method to handle settings change made in setting dialog

        Parameters
        ----------
        settings : TYPE
            DESCRIPTION.

        Returns
        -------
        None.

        '''
        # Update settings to setting dictionary
        self.settingDict[settings['Channel']]['Settings'] = settings['Settings']
        self.settingDict[settings['Channel']]['Multiplier'] = settings['Multiplier']
        # Update settings to measurent thread
        self.qout.put({'SettingDict':settings})
        # Update label accordingly
        self.channelGainLabelList[settings['Channel']].setText(str(settings['Multiplier']))
        
    def channelMenuPlottedClicked(self):
        '''
        Handler to changed amount of plotted graphs

        Returns
        -------
        None.

        '''
        self.selected_channels_plotted = []
        # Get channels names for all the selected channels
        for i,ach in enumerate(self.actionChsp):
            if ach.isChecked():
                # Add plotted channel
                self.selected_channels_plotted.append(i+1)
        
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
        
    def spinNloggingRateChanged(self):
        '''
        Communicate number of points per read operation to measurement program

        Returns
        -------
        None.

        '''
        self.N_logging = self.spinNlogging.value()
        self.qout.put({'Nlogging':self.N_logging})
        print(f'Number of point per read changed to {self.N_logging}')
        
        

    def radioClicked(self):
        '''
        Handler for event when radiobutton is toggled

        Returns
        -------
        None.

        '''
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
        x = np.linspace(0,1,self.Nchannel+1)
        rgb = mpl.colormaps['cool'](x)[np.newaxis, :, :3][0]*255
        rgb = rgb.astype(np.int64)
        for i in self.selected_channels_plotted:
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
            # Set color
            ci.setPen(QtGui.QColor(int(rgb[i][0]),rgb[i][1],rgb[i][2]))
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
              symbolPen = pg.mkPen(color=(0, 0, 255), width=0),                                      
              symbolBrush = pg.mkBrush(0, 150, 240, 250),
              symbolSize=7)
        # Set opacity
        self.mainCrv.setAlpha(0.9, False) 
        
        
        
    def updatePlots(self):
        '''
        Updates plots with new data

        Returns
        -------
        None.

        '''
        i=0
        nch = len(self.selected_channels_measured)
        try:
            # Extract all the data from queue
            while not self.queue.empty():
                # Extract data from queue
                data_in_arr = self.queue.get_nowait()
                for data_in in data_in_arr:
                    self.Npoints_total += 1
                    self.Ndata_in = len(data_in)
                    if self.disable_plotting:
                        break
                    # Add data to data array and check for size limit
                    datacount = self.Npoints_total*self.Ndata_in
                    # If there is too much data, pop first element out and add new data to array
                    if datacount > self.memory_limit:
                        for j,di in enumerate(data_in[:self.Nchannel+1]):
                            self.data[j].pop(0)
                            self.data[j].append(di)
                    # If datalimit is not reached, continue adding data to the array
                    else:
                        for j,di in enumerate(data_in[:self.Nchannel+1]):
                            self.data[j].append(di)
                            
                # Take last data_in and use it to update dataview
                for j,di in enumerate(data_in_arr[-1]):
                    if 0<j<=nch:
                        self.outputDataViewLabels[j-1].setText(f'{di:.3e}')
                    elif nch<j<=2*nch:
                        try:
                            self.rawDataViewLabels[j-nch-1].setText(f'{di:.3f}')
                        except IndexError:
                            print(f'Index error with index {j-nch-2}')
            i=0           
            # Add data to channel plots
            for ci in self.curves:
                iii = self.selected_channels_plotted[i]-1
                d_index = self.selected_channels_measured_index.index(iii)+1
                if self.scrollRadio.isChecked():
                    ci.setData(self.data[0][-self.scrollN:],self.data[d_index][-self.scrollN:])
                else:
                    ci.setData(self.data[0],self.data[d_index])
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
            if len(self.data[0])>1:
                self.pointsLabel.setText('Number of points: ' + str(self.Npoints_total))
                self.freqLabel.setText(f'Frequency: {self.Npoints_total/max(1,int(self.data[0][-1])):.2f} Hz')
                self.t_elapsedLabel.setText('Time elapsed: ' + str(datetime.timedelta(seconds=int(self.data[0][-1]))))
                
            # Update main plot labels if needed
            if self.labelChanged:
                # Update labels
                self.updateMainPlotLabels()
                # Labels updated, change status to False
                self.labelChanged = False
            if self.exitNow:
                sys.exit()
        except Exception:
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
        
    def thermChannelChanged(self):
        '''
        Method to set thermometer DAQ channel

        Returns
        -------
        None.

        '''
        # Get thermometer channel
        self.thermCh = self.comboThermCh.currentIndex()
        # Notify measurement program  for thermometer change
        self.qout.put({"ThermCh":self.thermCh})      
        print('Thermometer channel changed')
        
        
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
        self.mainPlt.setLabel('bottom', self.combo_list[ self.comboX.currentIndex()], **self.mainlabel_style)
        self.mainPlt.setLabel('left', self.combo_list[ self.comboY.currentIndex()], **self.mainlabel_style)
        
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

class QHLine(QtWidgets.QFrame):
    '''
    Modified code for horizontal line
    '''
    def __init__(self):
        super(QHLine, self).__init__()
        self.setFrameShape(QtWidgets.QFrame.HLine)
        self.setFrameShadow(QtWidgets.QFrame.Sunken)

        
def main(q1,q2,qin):
    app = QtWidgets.QApplication(sys.argv)
    app.setStyle("fusion")
    main = realTimeGraph()
    main.init_UI(Nchannel=16,continuous=False,memory_limit=1000000)
    main.setDataQueue(q1,q2,qin)
    main.Run()
    main.show()
    sys.exit(app.exec_())
   

class DeviceSettingDialog(QtWidgets.QDialog):
    '''
    Class for asking device settings for the experiment
    '''
    # Communicate dialog data via pyqtSignal
    accepted = QtCore.Signal(dict) #!!! Working also here

    def __init__(self,settings,paramsfile,channel,parent=None):
        super().__init__(parent)
        self.setWindowTitle("Device settings")
        
        # Set input dialog stylesheet
        self.setStyleSheet( "background-color:rgb(25, 35, 45);color:white")
        # Set stylesheets
        self.combostyle = """QComboBox { 
            background-color: rgb(43, 61, 79);
            selection-background-color: gray; 
            color : white; 
            border: 1px solid black; 
            padding :4px;
            selection-color:cyan;
            font-family: Arial;
            font-size:15 pt;
            }
            QComboBox::hover {
            background-color: rgb(55, 79, 102);
                }
            QListView{
            background-color: rgb(57, 68, 79);
            border: 1px solid black; 
            }
                """
        
        
        
        self.channel = channel
        self.settings = settings
        
        # Get available visa resources
        resm = pyvisa.ResourceManager()
        self.visa_list = resm.list_resources()
        
        #self.visa_list = ['GPIB0::20::INSTR','GPIB0::10::INSTR']
                
        # Create form
        form = QtWidgets.QFormLayout(self)
        # Open JSON file
        with open(paramsfile) as jf:
            paramsdict = json.load(jf)
        # Add controls corresponding to keys in paramsdict
        self.combo = {}
        self.ps = paramsdict['Settings']
        for key in self.ps:
            # Check if key is meant to be shown in dialog
            if self.ps[key]['toDialog']:
                # Check key type
                if self.ps[key]['type'] == 'QComboBox':
                    # Create combobox
                    combo_i = QtWidgets.QComboBox(self)
                    # Add all available values to combobox, handle GPIB channels differently
                    if key == 'GPIB channel':
                        combo_i.addItems(self.visa_list)
                    else:
                        combo_i.addItems([str(vi) for vi in self.ps[key]['values']])
                    # Set stylesheet
                    combo_i.setStyleSheet(self.combostyle)
                    # Set index to default or already applied value
                    try:
                        # Try to get current value
                        current_value = self.settings['Settings'][key]
                    except Exception as e:
                        # Fall back to default if no current value is set
                        current_value = self.ps[key]['default']
                    try:
                        if key == 'GPIB channel':
                            combo_i.setCurrentIndex(self.visa_list.index(current_value))
                        else:
                            combo_i.setCurrentIndex(self.ps[key]['values'].index(current_value))
                    except:
                        # Fall back to first index
                        combo_i.setCurrentIndex(0)
                    # Add combobox to list of comboboxes
                    self.combo[key] = combo_i
                    # Add to form
                    form.addRow(key, combo_i)
        self.btn = QtWidgets.QPushButton('OK')
        self.btn.clicked.connect(self.ok_pressed)
        form.addRow(self.btn)

    def ok_pressed(self):
        '''
        Handles event when ok button is pressed in the dialog

        Returns
        -------
        None.

        '''
        # Get settings from dialog
        settings = {}
        multip = 1
        # Iterate over the keys in setting dictionary
        for key in self.ps:
            # Take values only if values can be changed in dialog
            if self.ps[key]['toDialog']:
                # Extract values from comboboxes
                if self.ps[key]['type'] == 'QComboBox':
                    # Get current setting
                    if key == 'GPIB channel':
                        try:
                            ic = self.combo[key].currentIndex()
                        except:
                            ic = 0
                        val = self.visa_list[ic]
                    else:
                        ic = self.combo[key].currentIndex()
                        val = self.ps[key]['values'][ic]
                    settings[key] = val
                    # Get channel multiplier 
                    if 'Multiplier' in self.ps[key]:
                        # Check if value multiplies or divides channel value
                        if self.ps[key]['Multiplier'] == 'Multiply': #!!! Add new if clause if needed
                            multip=multip*val
                        elif self.ps[key]['Multiplier'] == 'Divide':
                            multip=multip/val
                        elif self.ps[key]['Multiplier'] == 'Multiply0.5':
                            multip=multip*val*0.5
            # Take default value
            else:
                settings[key] = self.ps[key]['default']
        values = {'Channel':self.channel,'Multiplier':multip,'Settings': settings}
        self.accepted.emit(values)
        self.accept()
    

class MetadataDialog(QtWidgets.QDialog):
    '''
    Class for asking users metadata for the experiment
    '''
    accepted = QtCore.Signal(dict)

    def __init__(self, measChannels,settingDict, available_devices, parent=None):
        super().__init__(parent)
        # Set up controls
        self.setWindowTitle("Measurement metadata")
        self.date = QtWidgets.QDateEdit()
        self.date.setDisplayFormat('MMM d, yyyy')
        self.date.setDate(QtCore.QDate.currentDate())
        self.sample = QtWidgets.QLineEdit()
        self.author_name = QtWidgets.QLineEdit()
        self.author_name.textEdited[str].connect(self.unlock)
        self.channelNameLabel = QtWidgets.QLabel()
        self.channelNameLabel.setText('Description')
        
        # Add controls to form
        form = QtWidgets.QFormLayout(self)
        form.addRow('Date', self.date)
        form.addRow('Sample', self.sample)
        form.addRow('Measured by', self.author_name)
        form.addRow('Channel',self.channelNameLabel)
        self.chs = {}
        for i,chi in enumerate(measChannels):
            lei = QtWidgets.QLineEdit()
            self.chs[chi] = lei
            form.addRow(chi, lei)
            # Set guess for channel description
            #devicename = settingDict[chi]
            #print(devicename)
            #paramsfile = available_devices[devicename]
            
        self.meas_desc = QtWidgets.QTextEdit()
        form.addRow('Measurement description', self.meas_desc)

        # Set up OK and SKIP buttons        
        self.btn = QtWidgets.QPushButton('OK')
        self.btn.setDisabled(True)
        self.btn.clicked.connect(self.ok_pressed)
        
        self.skip_btn = QtWidgets.QPushButton('SKIP')
        self.skip_btn.setEnabled(True)
        self.skip_btn.clicked.connect(self.skip)
        

        
        # Put buttons in a horizontal layout
        btn_layout = QtWidgets.QHBoxLayout()
        btn_layout.addWidget(self.btn)
        btn_layout.addWidget(self.skip_btn)
        
        form.addRow(btn_layout)

    def skip(self):
        '''
        Skip fomration of metadata

        Returns
        -------
        None.

        '''
        self.reject()

    def unlock(self, text):
        if text:
            self.btn.setEnabled(True)
        else:
            self.btn.setDisabled(True)

    def ok_pressed(self):
        '''
        Handles event when ok button is pressed in dialog

        Returns
        -------
        None.

        '''
        chdict = {}
        # Get channel names from dialog
        for chi in self.chs.keys():
            chdict[chi] = self.chs[chi].text()
        values = {'Date': self.date.date(),
                  'Author': self.author_name.text(),
                  'Sample': self.sample.text(),
                  'Description': self.meas_desc.toPlainText(),
                  'Channel names':chdict
                  }
        self.accepted.emit(values)
        self.accept()

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
        for i in range(16):
            data_out.append(np.random.rand(1)[0]+i)
        T = np.around((21+np.random.rand(1)[0])*1e-2,decimals=5)
        q1.put([data_out])
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
    
        
        
        
