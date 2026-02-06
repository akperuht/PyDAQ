# -*- coding: utf-8 -*-
"""
Python data acquisition code with UI

Collects, plots and logs data from chosen analog channels

Warning: still under development

@author: Aki Ruhtinas, aki.ruhtinas@gmail.com
"""
import sys
from UI.pyDAQ_UI_v2 import realTimeGraph
from Control_lib.DAQcontrol import DAQcontrol
from Control_lib.instrument_control import *
import nidaqmx
from nidaqmx.constants import AcquisitionType ,LoggingMode, LoggingOperation, WaitMode
from nidaqmx.stream_readers import AnalogMultiChannelReader
import Control_lib.thermometer_calib as tc
import uuid
from scipy.signal import *
from PyQt5 import QtWidgets
import numpy as np
import multiprocessing as mp
import traceback
import warnings


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
        
        self.memory_limit = 1000000
        
        self.N_logging = 100
        
        self.sens_change_wait = 100e-3 # Waiting time after lock-in sensitivity hase changed
        
        self.closeAtExit = False
        self.exit  = False
                
        self.N = 0 # Number of collected datapoints
        self.pathname = ""
        self.filename = "temp.txt"
        
        self.therm_calib_name = 'None'
        
        self.chunk_averaging = True
        self.rawdataout = True
        
        self.uuid = uuid.uuid4()
                        
        # Thermometer calibration
        self.therm_multiplier = 1000
        self.thermCh = 0

        self.plot_labels = ['Channel ' + str(i-1) for i in range(20)]
        self.plot_labels[0] = '#Time(s)'
        self.plot_Vunit_multip = 1 # Unit volts
        self.plot_Iunit_multip = 1 # Unit amperes
        
        # Preamplifier settings
        self.Gi = 1e-4
        self.Gv = 100
                
        # Set up queues for communication
        self.q0 = mp.Queue() # Queue for DAQ raw data
        self.q1 = mp.Queue() # Queue for data communication
        self.q2 = mp.Queue() # Dictionary queue for metadata
        self.q3 = mp.Queue() # Queue for data logging
        self.qin = mp.Queue() # Queue to get data from UI
        self.qr = mp.Queue() # Queue for communicating channel multipliers to measurement thread
        
        self.start = False
        
        self.stop_event = mp.Event()
        
        self.fname = None
        
        self.setup_data_collection = True
        
        self.daq_device_name = 'Dev1'
        
        self.DAQrange = [-10,10]
        
        self.settingDict = {}
        self.devicelist = {}
        
        
        
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
        # Forces fusion style for the app
        app.setStyle("fusion")
        main = realTimeGraph()
        # Get available channels 
        self.available_channels = getChannelNames(self.daq_device_name)
        # Initialize UI
        main.init_UI(filepath = self.defaultpathname, 
                     Nsamples = self.Nsamples, 
                     SampleRate = self.sample_rate,
                     available_channels = self.available_channels,
                     memory_limit = self.memory_limit,
                     rawdataout = self.rawdataout
                     )
        
        # Pass data queue to UI
        main.setDataQueue(self.q1,self.q2, self.qin)
        
        # Run the UI
        main.Run()
        main.show()
        sys.exit(app.exec_())
        
        
    def messageHandling(self,stop_event):
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
            self.processIncomingMessages(stop_event)              
        self.N = 0
        iter_time = 1
        # Data handling and control loop
        while True:
            # Handle communication to main UI
            self.processIncomingMessages(stop_event)
            while not self.start:
                self.processIncomingMessages(stop_event)
        sys.exit()
        
        
    def processIncomingMessages(self,stop_event):
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
            #print('===========================================================')
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
                # Clear the stop event 
                stop_event.clear()
                self.startEvent(stop_event)
                
            if 'stop' in measParamDict:
                self.start = False
                # Set stop event flag
                stop_event.set()
                
            # Get thermometer calibration from GUI
            if 'ThermCalibName' in measParamDict:
                print(f'Calibration changed to {self.therm_calib_name}')
                self.therm_calib_name = str(measParamDict['ThermCalibName'])
                
            if 'ThermCh' in measParamDict:
                self.thermCh = int(measParamDict['ThermCh'])
                
            # Get filename from GUI
            if 'fname' in measParamDict:
                self.fname = str(measParamDict['fname'])
                print(self.fname)
            
            # Change sample rate on the fly
            if 'SampleRate' in measParamDict:
                self.sample_rate = int(measParamDict['SampleRate'])
                print('Sample rate: ' + str(self.sample_rate))

            # Change amount of points collected before written into file
            if 'Nlogging' in measParamDict:
                self.N_logging = int(measParamDict['Nlogging'])
                print('Sample rate: ' + str(self.N_logging))

            if 'measChannels' in measParamDict:
                # Read channels from dictionary
                self.channels = measParamDict['measChannels']
                # Initialize multipliers
                self.multips = np.ones(len(self.channels)+1)
                # Setup flag to update data collection
                self.setup_data_collection =True
                
            if 'datalabels' in measParamDict:
                # Setup channel names
                self.plot_labels = measParamDict['datalabels']
                
            # Check thermometer calibration name
            if 'ThermCalibName' in measParamDict:
                self.therm_calib_name = measParamDict['ThermCalibName']
                
            # Change samples/point on the fly
            if 'Nsamples' in measParamDict:
                self.Nsamples = int(measParamDict['Nsamples'])
                # Update data array length accordingly
                self.out = np.empty(shape=(len(self.channels),self.Nsamples))
                print('Samples/point: ' + str(self.Nsamples))
            
            if 'SettingDict' in measParamDict:
                # Get parameters from input dictionary
                setdict = measParamDict['SettingDict']
                setting_chi = setdict['Settings']
                multip_chi = setdict['Multiplier']
                chi = setdict['Channel']
                # Parse parameters to settingDict
                self.settingDict[chi] = {'Multiplier' : multip_chi,'Settings' : setting_chi}
                # Handle parameter change
                self.handleSettingDictChange(chi)
            # Get UUID for the measurement
            if 'UUID' in measParamDict:
                self.uuid = measParamDict['UUID']
                
                         
    def handleSettingDictChange(self,channel):
        '''
        Method to handle event when channel settings are changed

        Parameters
        ----------
        channel : str
            Channel whose settings has been modified

        Returns
        -------
        None.

        '''
        # Add 1 here because time is never multiplied
        self.multips = [1]
        # Iterate through the channels and extract channel multipliers
        for chi in self.channels:
            try:
                multip_chi = self.settingDict[chi]['Multiplier']
            except:
                multip_chi = 1
            self.multips.append(multip_chi)
        # Communicate channel multiplier to measurement thread
        self.qr.put(self.multips)
        
        # Communicate device settings to the device
        if self.settingDict[channel]['Settings']['Remote']:
            # Check device type here
            dev_name = self.settingDict[channel]['Settings']['Device']
            dev_gbip = self.settingDict[channel]['Settings']['GPIB channel']
            # Check if GPIB channel already exists and it is assigned to wanted device
            if dev_gbip in self.devicelist and self.devicelist[dev_gbip]['Name'] == dev_name:
                # Apply settings to the device
                self.devicelist[dev_gbip]['Device'].apply_settings(self.settingDict[channel]['Settings'])
            # Device does not exist, so initialize new one
            else: #!!! Write here own if clause for new device
                # Initialize AVS-47
                if dev_name == 'AVS-47':
                    # Initalize AVS-47
                    try:
                        # Make AVS-47 device
                        avs = AVS47(dev_gbip,0)
                        # Apply settings       
                        avs.apply_settings(self.settingDict[channel]['Settings'])
                        # Add device to the devicelist
                        self.devicelist[dev_gbip]= {'Device':avs,'Name':'AVS-47'}
                    except Exception as e:
                        traceback.print_exc()
                        warnings.warn('Not able to connect to AVS-47')
        
            
    def processData(self,stop_event,q0,q1,q3,qr):
        '''
        process measured data and send it forward

        Returns
        -------
        None.

        '''
        # Initialize data arrays
        if self.chunk_averaging:
            output = np.zeros(shape=(self.N_logging,len(self.channels)+1))
        else:
            output = np.zeros(shape=(self.N_logging*self.Nsamples,len(self.channels)+1))
        # Infinite loop
        multips = self.multips
        print(multips)
        # Select calibration function
        # Currently available: [Dipstick','Morso','Ling','Kanada','Noiseless']
        if self.therm_calib_name == 'Dipstick':
            self.therm_calib = tc.calibration_dipstick
        elif self.therm_calib_name == 'Morso':
            self.therm_calib = tc.calibration_morso
        elif self.therm_calib_name == 'Ling':
            self.therm_calib = tc.calibration_Ling
        elif self.therm_calib_name == 'Kanada':
            self.therm_calib = tc.calibration_Kanada
        else:
            self.therm_calib = lambda x:x
        # Column where thermometer data is
        thermcol = self.thermCh + 1
        # Start while loop
        while not stop_event.is_set():
            # Read channel multipliers and get only the latest one
            while not self.qr.empty() and not stop_event.is_set():
                multips = self.qr.get_nowait()
            # Read channel measurement data
            n_out = 0
            # Take data out of DAQ until desired amount of data is fetched
            while n_out < self.N_logging and not stop_event.is_set():
                # Take all the data from queue
                try:
                    rawdataout = self.q0.get_nowait()
                except:
                    continue
                timestamp = rawdataout[0]
                out = rawdataout[1]
                # Calculate average for each channel
                if self.chunk_averaging:
                    # Add one row to output array
                    output[n_out] = np.concatenate(([timestamp],np.average(out, axis=1)))
                else:
                    # Generate time array. Startpoint is the timestamp point and not hardware time, expect small deviation from real value
                    timearr = timestamp - np.linspace(0,(1/self.sample_rate)*(self.Nsamples-1),self.Nsamples)
                    # Add time as a first channel and put data to output array
                    output[n_out*self.Nsamples:(n_out+1)*self.Nsamples] = np.transpose(np.concatenate(([timearr[::-1]],out)))
                n_out += 1
            
            # Multiply output with channel multipliers
            outputm = np.multiply(output,multips)
            # Apply thermometer function to only one column of the data
            if self.therm_calib_name != 'None':
                try:
                    outputm[:,thermcol] = np.apply_along_axis(self.therm_calib, 0, outputm[:,thermcol])
                except:
                    print('ERROR in temperature calculation')
            # Send data to datalogging queue with raw data without multiplication
            if self.rawdataout:
                # Add raw data to output
                dataout = np.concatenate((outputm,np.delete(output,0,axis=1)),axis=1)
            else:
                dataout = outputm
            # Send data to logging queue
            q3.put(dataout)
            # Send multiplied data to plotting queue
            q1.put(dataout) #!!! Averaging again for plotting!
        print('Data processing stopped')
        sys.exit()
            
    def dataLogger(self,stop_event,q3):
        '''
        Log data to file in own process

        Returns
        -------
        None.

        '''
        while not stop_event.is_set():
            # Iterate data queue until empty
            while not self.q3.empty():
                # Get data from measurement thread
                data = self.q3.get_nowait()
                # write data to file
                with open(self.fname,'a+') as f:
                    # Write every row in data
                    for di in data:
                        f.write(" ".join(str(item) for item in di))
                        f.write("\n")
        print('Logging stopped')
        sys.exit()
            
            
    def startEvent(self,stop_event):
        '''
        Handles event when measurement is started

        Returns
        -------
        None.

        '''
        with open(self.fname,'a+') as f:
            # Write down unique identifier
            f.write('# UUID: '+str(self.uuid))
            f.write("\n")
            # Write column labels
            for pi in self.plot_labels[:len(self.channels)+1]:
                f.write(pi + " ")
            # Write raw data labels if necessary
            if self.rawdataout:
                for chi in self.channels:
                    f.write(chi + " ")
            f.write("\n")
        # Start data collection
        
        # initialize DAQ control class
        daq = DAQcontrol(self.channels)

        # Start logging data to multiprocessing queue continuously
        measData = mp.Process(target = daq.continous_Nread,args = (stop_event,self.q0,self.sample_rate, self.Nsamples))
        measData.start()
        print('Data logging started')
        # Start processing thread
        proData = mp.Process(target = self.processData,args = (stop_event,self.q0,self.q1,self.q3,self.qr))
        proData.start()
        print('Data processing started')
        
        # Data logging thread
        logData = mp.Process(target = self.dataLogger,args = (stop_event,self.q3))
        logData.start()
        print('Data writing to file started')
            
            
    
    def Exit(self):
        '''
        Exit system

        Returns
        -------
        None.

        '''
        sys.exit()
        
def testfunction(Nchannels,Nsamples):
    '''
    Function to test data aquisition system

    Parameters
    ----------
    Nchannels : int
        Number of measurement channels in use.
    Nsamples : int
        Number of samples.

    Returns
    -------
    out
        output array with random numbers

    '''
    return np.random.rand(Nchannels,Nsamples)

def getChannelNames(name):
    '''
    Function to generate channel names for testing

    Parameters
    ----------
    name : TYPE
        DESCRIPTION.

    Returns
    -------
    list
        DESCRIPTION.

    '''
    return ["Dev1/ai0","Dev1/ai1","Dev1/ai2","Dev1/ai3","Dev1/ai4","Dev1/ai5","Dev1/ai6","Dev1/ai7"]
        
if __name__ == '__main__':
        # Initialize class
        meas = pyDAQmeas()
        # Device name, change if needed
        #meas.daq_device_name = 'Dev1'
        meas.daq_device_name = 'Dev1'
        
        # Settling time, 10e-3 is good starting point
        meas.settling_time = 10e-3
        meas.N_logging = 10
        meas.memory_limit = 1000000
        
        meas.disable_plotting = False
        
        meas.chunk_averaging = True
        meas.rawdataout = True
        
        meas.stop_event = mp.Event()
        
        # Default values for different variables
        # All of these can be changed from the GUI also
        meas.therm_calib_name = "None"
        meas.Nsamples = 5000
        meas.sample_rate = 5e4
        meas.defaultpathname = r""
        meas.filename = r'testing.data'
        meas.therm_multiplier = 1000
        meas.channels=["Dev1/ai0","Dev1/ai1","Dev1/ai2"]

        
        # Start background and GUI threads
        worker = mp.Process(target = meas.messageHandling,args=(meas.stop_event,))
        worker.start()
        # Start data plotting GUI
        meas.startPlotting()
        

         
    
    
    
    
    
    
    