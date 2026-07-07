# -*- coding: utf-8 -*-
"""
Python data acquisition code with UI

Collects, plots and logs data from chosen analog channels

Warning: still under development

@author: Aki Ruhtinas, aki.ruhtinas@gmail.com
"""
import sys
from UI.pyDAQ_UI_v3 import realTimeGraph
from Control_lib.DAQ_lib import DAQ
from Control_lib.instrument_control import *
import nidaqmx
from nidaqmx.constants import AcquisitionType ,LoggingMode, LoggingOperation, WaitMode
from nidaqmx.stream_readers import AnalogMultiChannelReader
import Control_lib.thermometer_calib as tc
import uuid
from scipy.signal import *
from PySide6 import QtWidgets
import numpy as np
import multiprocessing as mp
import traceback
import warnings
import logging
import h5py
import pandas as pd

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
        self.q00 = mp.Queue() # Queue for DAQ raw data
        self.q01 = mp.Queue() # Queue for DAQ raw data
        self.q02 = mp.Queue() # Queue for DAQ raw data
        self.q03 = mp.Queue() # Queue for DAQ raw data
        self.q04 = mp.Queue() # Queue for DAQ raw data

        self.data_queues = [self.q00,self.q01,self.q02,self.q03,self.q04]
        
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

        self.DAQinterfaces = {}
        self.DAQsettingDict = {}
        
        
        
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
        sys.exit(app.exec())
        
        
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

            if 'DAQSettingDict' in measParamDict:
                # Get parameters from input dictionary
                setdict = measParamDict['DAQSettingDict']
                setting_daqchi = setdict['Settings']
                chi = setdict['Channel']
                # Parse parameters to settingDict
                self.DAQsettingDict[chi] = {'Settings' : setting_daqchi}
                # Handle parameter change
                self.handleDAQSettingDictChange(chi)

            if 'DAQinterfaces' in measParamDict:
                # Get DAQ interfaces from input dictionary
                self.DAQ_interfaces = measParamDict['DAQinterfaces']

            if 'DAQSettingDict' in measParamDict:
                # Get parameters from input dictionary
                setdict = measParamDict['DAQSettingDict']
                setting_daqchi = setdict['Settings']
                chi = setdict['Channel']
                # Parse parameters to settingDict
                self.DAQsettingDict[chi] = {'Settings' : setting_daqchi}
                # Handle parameter change
                self.handleDAQSettingDictChange(chi)

            # Get UUID for the measurement
            if 'UUID' in measParamDict:
                self.uuid = measParamDict['UUID']

    def handleDAQSettingDictChange(self,channel):
        '''
        Method to handle event when DAQ settings are changed

        Parameters
        ----------
        channel : str
            DAQ whose settings has been modified

        Returns
        -------
        None.

        '''       
        # Communicate device settings to the device
        if self.DAQsettingDict[channel]['Settings']['Remote']:
            # Check device type here
            dev_name = self.DAQsettingDict[channel]['Settings']['Device']
            conn_type = self.DAQsettingDict[channel]['Settings']['Connection type']
            if conn_type == 'GPIB':
                dev_gbip = self.DAQsettingDict[channel]['Settings']['GPIB channel']
                            # Check if GPIB channel already exists and it is assigned to wanted device
                if dev_gbip in self.devicelist and self.devicelist[dev_gbip]['Name'] == dev_name:
                    # Apply settings to the device
                    self.devicelist[dev_gbip]['Device'].apply_settings(self.DAQsettingDict[channel]['Settings'])
                            # Device does not exist, so initialize new one
                else: #!!! Write here own if clause for new device
                    # Initialize AVS-47
                    if dev_name == 'AVS-47':
                        # Initalize AVS-47
                        try:
                            # Make AVS-47 device
                            avs = AVS47(dev_gbip,0)
                            # Apply settings       
                            avs.apply_settings(self.DAQsettingDict[channel]['Settings'])
                            # Add device to the devicelist
                            self.devicelist[dev_gbip]= {'Device':avs,'Name':'AVS-47'}
                        except Exception as e:
                            traceback.print_exc()
                            warnings.warn('Not able to connect to AVS-47')
            elif conn_type.startswith('IP'):
                if conn_type == 'IPv4 Address':
                    dev_ip = self.DAQsettingDict[channel]['Settings']['IPv4 Address']
                elif conn_type == 'IPv6 Address':
                    dev_ip = self.DAQsettingDict[channel]['Settings']['IPv6 Address']
                if dev_ip in self.devicelist and self.devicelist[dev_ip]['Name'] == dev_name:
                    # Apply settings to the device
                    self.devicelist[dev_ip]['Device'].apply_settings(self.DAQsettingDict[channel]['Settings'])
                # Device does not exist, so initialize new one
                else: #!!! Write here own if clause for new device
                    pass
            else:
                warnings.warn('Unknown connection type for DAQ interface')
                return


                         
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
        self.multips = []
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
        
    def processData(self,stop_event,used_queues,q1,q3,qr):
        '''
        process measured data and send it forward

        Returns
        -------
        None.

        '''
        multipsdaq = {}
        # Initialize data arrays
        output = {}
        outputm = {}
        Nsm = {}
        i_ch = 0
        # Iterate through DAQ interfaces to get correct size for the data
        for daqch in self.DAQsettingDict:
            # Set up data arrays
            if self.chunk_averaging:
                Nch = len(self.DAQsettingDict[daqch]['Settings']['Channels'])
                output[daqch] = np.zeros(shape = (self.N_logging,Nch+1))
                outputm[daqch] = np.zeros(shape = (self.N_logging,Nch+1))
            else:
                Nch = len(self.DAQsettingDict[daqch]['Settings']['Channels'])
                try:
                    Nsmi = int(self.DAQsettingDict[daqch]['Settings']['Number of samples'])
                except:
                    Nsmi = 1
                Nsm[daqch] = Nsmi
                output[daqch] = np.zeros(shape = (self.N_logging*Nsmi,Nch+1))
                outputm[daqch] = np.zeros(shape = (self.N_logging*Nsmi,Nch+1))
            
            # Construct multipliers and take time into account
            multipsdaq[daqch] = [1] + self.multips[i_ch:i_ch + Nch]
            if len(multipsdaq[daqch]) != Nch+1:
                multipsdaq[daqch] = np.ones(len(multipsdaq[daqch]))
            i_ch += Nch
        
        # Infinite loop
        print(f'Channel multipliers: {multipsdaq}')
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
            data_received = [False for qi in used_queues]
            # Take data out of DAQ until desired amount of data is fetched
            while n_out < self.N_logging and not stop_event.is_set():
                # Take all the data from queues
                for i,(daqch,qi) in enumerate(zip(used_queues.keys(),used_queues.values())):
                    try:
                        datain = qi.get_nowait()
                        data_received[i] = True
                    # If something happens in data extraction, change flag to false
                    except Exception as e:
                        data_received[i] = False
                        continue
                    try:
                        # Calculate average for each channel
                        if self.chunk_averaging:
                            # Add one averaged row to output array
                            output[daqch][n_out] = np.average(datain, axis=1)
                        else:
                            output[daqch][n_out*Nsm[daqch]:(n_out+1)*Nsm[daqch]] = np.transpose(datain)
                        # Multiply output with channel multipliers
                        outputm[daqch] = np.multiply(output[daqch],multipsdaq[daqch])
                    except Exception as e:
                        logging.info(f'Error occurred {e}')
                # Check if there is incoming data in any of the queues
                if not any(data_received):
                    # Continue to next iteration if no data is received
                    continue
                n_out += 1
            
            # Apply thermometer function to only one column of the data
            #outputm[:,thermcol] = np.apply_along_axis(self.therm_calib, 0, outputm[:,thermcol])
            # Send data to datalogging queue with raw data without multiplication
            if self.rawdataout:
                # Send data to logging queue
                q3.put({'Data':outputm,'rawdata':output})
            else:
                q3.put({'Data':outputm})
                
            # Send multiplied data to plotting queue
            # Flatten the data
            output_flatten = np.hstack([outputm[k] if k == 0 else outputm[k][:, 1:]
                for k in sorted(outputm)
            ])
            print(output_flatten.shape)
            q1.put(output_flatten) #!!! Averaging again for plotting!
        print('Data processing stopped')
        sys.exit()

    '''
    def dataLogger(self,stop_event,q3):
        while not stop_event.is_set():
            # Iterate data queue until empty
            while not self.q3.empty():
                # Get data from measurement thread
                data = self.q3.get_nowait()
                df = pd.DataFrame(data)
                print('Data received')
                with pd.HDFStore(self.filename) as file:
                    file.append(
                        "Measurement",
                        df,
                        format="table",
                        data_columns=True
                    )
        print('Logging stopped')
        sys.exit()
    '''

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
        # Start data collection
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
        # initialize DAQ control class
        daq = DAQ()

        # Log same start time for all processes for syncing
        starttime = time.perf_counter()

        self.used_queues = {}
        for daqch,daqi in zip(self.DAQ_interfaces.keys(), self.DAQ_interfaces.values()):
            qi = self.data_queues[daqch]
            settings = self.DAQsettingDict[daqch]['Settings']
            mi = None
            if self.testmode:
                print('Testing mode on, no data acquisition')
                mi = mp.Process(target = daq.continous_Nread_test,args = (stop_event,starttime,self.channels,qi,self.sample_rate, self.Nsamples))
                break
            elif daqi == 'Moku Go':
                try:
                    mi = mp.Process(target = daq.MokuGo_continuous_Nread,
                                    args = (stop_event,starttime,qi,settings))
                except Exception as e:
                    print(f"Error occurred while initializing Moku Go: {e}")
            elif daqi == 'NI DAQ':
                mi = mp.Process(target = daq.NiDAQmx_continous_Nread,args = (stop_event,starttime,self.channels,qi,self.sample_rate, self.Nsamples))
            elif daqi == 'AVS-47':
                mi = mp.Process(target = daq.AVS47_continuous_read,args = (stop_event,starttime,qi,self.sample_rate, self.Nsamples))
            else:
                mi = None
            # Add thread and queue to the list of used threads and queues
            self.used_queues[daqch] = qi
            # Start the data acquisition process
            mi.start()
            print(f"Started data acquisition for {daqi} on DAQ interface {daqch}")
            print(f"Number of used queues: {len(self.used_queues)}")

        print('Data logging started')

        # Start processing thread
        try:
            args = (stop_event,self.used_queues,self.q1,self.q3,self.qr)
            proData = mp.Process(target = self.processData,
                                args = args)
            proData.start()
            print('Data processing started')
        except Exception as e:
            traceback.print_exc()
            logging.error(f"Error occurred while starting data processing: {e}")

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
        meas.daq_device_name = 'MokuGo'
        meas.moku_go_ip = '[fe80::7269:79ff:feb9:7b5c]'
        
        meas.testmode = False

        # Settling time, 10e-3 is good starting point
        meas.settling_time = 10e-3
        meas.N_logging = 10
        meas.memory_limit = 1000000
        
        meas.disable_plotting = False
        
        meas.chunk_averaging = True
        meas.rawdataout = True
        
        meas.stop_event = mp.Event()
        
        # Default values for different variables
        # All of these can be changed from the GUI
        meas.therm_calib_name = "None"
        meas.Nsamples = 5000
        meas.sample_rate = 5e4
        meas.defaultpathname = r""
        meas.filename = r'testing.data'
        meas.therm_multiplier = 1000
        #meas.channels=["Dev1/ai0","Dev1/ai1","Dev1/ai2"]
        meas.channels=["time","ch1","ch2"]

        
        # Start background and GUI threads
        worker = mp.Process(target = meas.messageHandling,args=(meas.stop_event,))
        worker.start()
        # Start data plotting GUI
        meas.startPlotting()
        

         
    
    
    
    
    
    
    