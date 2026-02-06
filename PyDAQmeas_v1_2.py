# -*- coding: utf-8 -*-
"""
Python data acquisition code with UI

Collects, plots and logs data from chosen analog channels

Warning: still under development

@author: Aki Ruhtinas, aki.ruhtinas@gmail.com
"""
import sys
from pyDAQ_UI_v1 import realTimeGraph
from DAQcontrol import *
from instrument_control import *
from thermometer_calib import *
import nidaqmx
import uuid
from scipy.signal import *

from PyQt5 import QtWidgets
import matplotlib.pyplot as plt
import numpy as np
import time
import multiprocessing as mp
import traceback
import h5py
import signal


class pyDAQmeas():
    '''
    Class for data acquisition
    '''
    def __init__(self):
        self.channels=["Dev1/ai0","Dev1/ai1","Dev1/ai2"]  # Channels to read
        self.Nsamples = 1000 # Number of samples per each point
        self.sample_rate = 5e4 # DAQ card sampling rate
        self.settling_time = 15e-3 # Settling time after param setting
        self.wait_time = 10e-3 # Wait 10 ms between runs
        
        self.sens_change_wait = 100e-3 # Waiting time after lock-in sensitivity hase changed
        
        self.closeAtExit = False
        self.exit  = False
                
        self.N = 0 # Number of collected datapoints
        self.pathname = ""
        self.filename = "temp.txt"
        
        self.therm_calib_name = "Dipstick"
        
        self.uuid = uuid.uuid4()
                        
        # Thermometer calibration
        self.therm_multiplier = 1000
        self.Rtemp_ch = 0

        self.plot_labels = ['Channel ' + str(i-1) for i in range(20)]
        self.plot_labels[0] = '#Time(s)'
        self.plot_Vunit_multip = 1 # Unit volts
        self.plot_Iunit_multip = 1 # Unit amperes
        
        # Preamplifier settings
        self.Gi = 1e-4
        self.Gv = 100
                
        # Set up queues for communication
        self.q1 = mp.Queue() # Queue for data communication
        self.q2 = mp.Queue() # Dictionary queue for metadata
        self.q3 = mp.Queue() # Queue for data logging
        self.qin = mp.Queue() # Queue to get data from UI
        
        self.start = False
        
        self.fname = None
        
        self.setup_data_collection = True
        
        self.daq_device_name = 'Dev1'
        
        
    def startPlotting(self):
        '''
        Function to start plotting

        Parameters
        ----------
        Nchannel : int
            Number of data channels

        Returns
        -------
        None.

        '''
        # Start plotting application
        app = QtWidgets.QApplication(sys.argv)
        main = realTimeGraph()
        # Get available channels 
        self.available_channels = getChannelNames(self.daq_device_name)
        # Initialize UI
        main.init_UI(filepath = self.defaultpathname, 
                     Nsamples = self.Nsamples, 
                     SampleRate = self.sample_rate,
                     available_channels = self.available_channels)
        # Pass data queue to UI
        main.setDataQueue(self.q1,self.q2, self.qin)
        
        # Run the UI
        main.Run()
        main.show()
        sys.exit(app.exec_())
     
            
        
    def readData(self):
        '''
        Read data from the DAQ card

        Parameters
        ----------
        q1 : multiprocessing.queue
            queue to pass the data 
        q2 : multiprocessing.queue
            dictionary queue to pass the metadata
        Ndata : int
            maximum number of collected datapoints

        Returns
        -------
        None.

        '''
        while not self.start:
            self.processIncomingData()              
        # Get starting time for measurement
        starttime=time.perf_counter()
        # Initialize data collection
        self.initDataCollection()
        data = []
        self.N = 0
        iter_time = 1
        # Data acquisition and control loop
        while True:
            # Handle communication to main UI
            self.processIncomingData()
            while not self.start:
                self.processIncomingData()
            if self.setup_data_collection:
                self.initDataCollection()
                data = []
            # Get timestamp
            t1=time.perf_counter()
            timestamp = t1-starttime
            # Collect data from DAQ card
            self.daq.request_data(self.out,self.sample_rate,self.Nsamples)          
            # Get temperature
            Rtemp = np.average(self.out[self.Rtemp_ch])
            # Calculate temperature
            T=0
            if self.therm_calib_name == "Dipstick_old":
                T = calibration_dipstick(Rtemp,self.therm_multiplier)
            elif self.therm_calib_name == "Dipstick":
                T = calibration_dipstick_new(Rtemp,self.therm_multiplier)
            elif self.therm_calib_name == "Kanada_old":
                T = calibration_Kanada(Rtemp,self.therm_multiplier)
            elif self.therm_calib_name == "Kanada":
                T = calibration_Kanada_lowtemp_2022(Rtemp,self.therm_multiplier)
            elif self.therm_calib_name == "Ling":
                T = calibration_Ling(Rtemp,self.therm_multiplier)
            else:
                T = calibration_dipstick_new(Rtemp,self.therm_multiplier)	

            
            data=[t1-starttime]
            # Put all of the data to data array
            for i in range(len(self.out)):
                data.append(np.average(self.out[i]))
            # Transfer data to queue and select what to plot
            self.q1.put(data)
            # Check if start button is press
            if self.newstart:
                # Write down unique identifier for first iteration
                self.dataLogger('# UUID: '+str(self.uuid),spaces = False)
                # Write down datalabels for first iteration
                self.dataLogger(self.plot_labels[:len(self.channels)+1])
                self.newstart = False
            # Write data to a file
            self.dataLogger(data)
            # Construct metadata queue
            self.q2.put({"Npoints" : self.N, 
                         "Temperature": T, 
                         "Freq": str(np.around(1/iter_time,decimals=2))+" Hz",
                         })
            # Time between iterations
            time.sleep(self.wait_time)
            # Calculate iteration time
            t2 = time.perf_counter()
            iter_time = abs(t1-t2)
            self.N+=1
            
        # close plotting window at exit
        if self.closeAtExit:
            self.exit = True
            self.q1.put('Exit')
        sys.exit()
         
        
    def initDataCollection(self):
        '''
        Method for initializing data collection

        Returns
        -------
        None.

        '''
        print(self.channels)
        # Initialize array for data collection
        self.out = np.empty(shape=(len(self.channels),self.Nsamples))
        # Initialize DAQ control class
        self.daq = DAQcontrol(self.channels)
        self.setup_data_collection = False
        
        
    def processIncomingData(self):
        '''
        Method to process data sent by UI
        Changes Gv, Gi and Rtherm_multip when these are changed in UI

        Returns
        -------
        None.

        '''
        # Read if values are changed in UI
        while not self.qin.empty():
            # Extract data from queue
            measParamDict = self.qin.get_nowait()
            print('===========================================================')
            if 'Gv' in measParamDict:
                self.Gv = float(measParamDict['Gv'])
                print('Preamplifier gain changed: Gv = ' + str(self.Gv))
            if 'Gi' in measParamDict:
                self.Gi = float(measParamDict['Gi'])
                print('Preamplifier gain changed: Gi = ' + str(self.Gi))
            if 'Rtherm_multip' in measParamDict:
                self.therm_multiplier = float(measParamDict['Rtherm_multip'])
                print('Resistance bridge multiplier changed: Multiplier = ' + str(self.therm_multiplier))
            if 'start' in measParamDict:
                self.start = True
                self.newstart = True
            if 'stop' in measParamDict:
                self.start = False
                
            # Get thermometer calibration from GUI
            if 'ThermCalibName' in measParamDict:
                self.therm_calib_name = str(measParamDict['ThermCalibName'])
                
            if 'ThermCh' in measParamDict:
                self.Rtemp_ch = int(measParamDict['ThermCh'])
                
            # Get filename from GUI
            if 'fname' in measParamDict:
                self.fname = str(measParamDict['fname'])
                print(self.fname)
            
            # Change sample rate on the fly
            if 'SampleRate' in measParamDict:
                self.sample_rate = int(measParamDict['SampleRate'])
                print('Sample rate: ' + str(self.sample_rate))

            if 'measChannels' in measParamDict:
                # Read channels from dictionary
                self.channels = measParamDict['measChannels']
                # Setup flag to update data collection
                self.setup_data_collection =True
                
            if 'measChannelsIndices' in measParamDict:
                # Setup channel names
                self.plot_labels = ['#Time(s)'] + ['Channel '+str(i) for i in measParamDict['measChannelsIndices']]

            # Change samples/point on the fly
            if 'Nsamples' in measParamDict:
                self.Nsamples = int(measParamDict['Nsamples'])
                # Update data array length accordingly
                self.out = np.empty(shape=(len(self.channels),self.Nsamples))
                print('Samples/point: ' + str(self.Nsamples))
                
            print('===========================================================')
        
        
    def dataLogger(self,data,spaces = True):
        '''
        Function for data logging and communication to external plotting UI

        Returns
        -------
        None.

        '''
        # write data to file
        #self.fname = self.defaultpathname+"\\"+self.filename
        with open(self.fname,'a+') as f:
            if spaces:
                f.write(" ".join(str(item) for item in data))
                f.write("\n")
            else:
                f.write(data)
                f.write("\n")
    
    def Exit(self):
        '''
        Exit system

        Returns
        -------
        None.

        '''
        sys.exit()
        
    def Run(self):
        '''
        Run the measurement 

        Returns
        -------
        None.

        '''
        # Start data reading and logging in different threads
        worker = mp.Process(target = self.readData)
        worker.start()
        # Start data plotting GUI
        self.startPlotting(len(self.channels))

if __name__ == '__main__':
        # Initialize class
        meas=pyDAQmeas()
        # Device name, change if needed
        #meas.daq_device_name = 'Dev1'
        meas.daq_device_name = 'PXI1Slot2'
        
        # Settling time, 10e-3 is good starting point
        meas.settling_time = 10e-3
        
        # Default values for different variables
        # All of these can be changed from the GUI also
        meas.therm_calib_name = "Dipstick"
        meas.Nsamples = 4000
        meas.sample_rate = 5e4
        meas.defaultpathname = r""
        meas.filename = r'testing.data'
        meas.therm_multiplier = 1000
        meas.channels=["PXI1Slot2/ai0","PXI1Slot2/ai1","PXI1Slot2/ai2"]
        
        # Start background and GUI threads
        worker = mp.Process(target = meas.readData)
        worker.start()
        # Start data plotting GUI
        meas.startPlotting()
        

         
    
    
    
    
    
    
    