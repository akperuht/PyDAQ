# -*- coding: utf-8 -*-
"""
Created on Wed Sep 23 16:39:17 2020

@author: akperuht
"""
import numpy as np
import matplotlib.pyplot as plt
import nidaqmx
from nidaqmx.constants import AcquisitionType ,LoggingMode, LoggingOperation, WaitMode
from nidaqmx.stream_readers import AnalogMultiChannelReader
from nidaqmx.stream_writers import AnalogMultiChannelWriter
import threading 
import multiprocessing as mp
from queue import Queue, Empty
import time
import multiprocessing as mp
from time import perf_counter

class DAQcontrol():
    def __init__(self,channels=None):
        '''
        class constructor

        Parameters
        ----------
        channels : list(string), optional
            DAQ channels from which data is to be collected. The default is None.
        Returns
        -------
        None.

        '''
        self.channels=channels
        self.data = []
        self.numpoints = 0
        self.maxpoints = np.inf
        self.stop = False
        self.range = [-10,10]
        self.lock = False
        self.task = None
        self.write_task = None
    
    def Stop(self):
        '''
        Stops all the running data collections

        Returns
        -------
        None.

        '''
        self.stop=True
    
    def log_data(self, sample_rate, N_samples,filename):       
        # Start task 
        with nidaqmx.Task() as task:
            for ch in self.channels:
                task.ai_channels.add_ai_voltage_chan(ch,min_val=self.range[0], max_val=self.range[1])
            # Set up the logging to a file
            task.in_stream.configure_logging(filename,logging_mode=LoggingMode.LOG,group_name='voltage',operation=LoggingOperation.OPEN_OR_CREATE )
            # Setting the rate of the Sample Clock and the number of samples to acquire
            task.timing.cfg_samp_clk_timing(sample_rate, source="", sample_mode=AcquisitionType.CONTINUOUS, samps_per_chan=N_samples)
            # Starting the loggin operation
            task.start()
            time.sleep(5)
            task.stop()
       
    def collect_data(self, q, sample_rate, N_samples):
        '''
        Function to set up continuous collection of data using NI-DAQmx interface

        Parameters
        ----------
        q : queue
            Queue where to update the data
        sample_rate : float
            Specifies the sampling rate in samples per channel per second
        N_samples : int
            NI-DAQmx uses this value to determine the buffer size. Function returns an error if the specified value is negative.
            
        Returns
        -------
        None.
        '''
        
        # Initialize array for data reader
        out=np.empty(shape=(len(self.channels),N_samples))
        # Start task 
        with nidaqmx.Task() as task:
            for ch in self.channels:
                task.ai_channels.add_ai_voltage_chan(ch,min_val=self.range[0], max_val=self.range[1])
            # Setting the rate of the Sample Clock and the number of samples to acquire
            task.timing.cfg_samp_clk_timing(sample_rate, source="", sample_mode=AcquisitionType.CONTINUOUS, samps_per_chan=N_samples)
            # Initializing new stream reader for the task
            self.reader = AnalogMultiChannelReader(task.in_stream)
            try:
                # Perform reading
                while not self.stop:
                    self.numpoints+=1 # Keep track how many points are read
                    # Read datapoints from DAQ to out array
                    self.reader.read_many_sample(data = out,number_of_samples_per_channel = N_samples)
                    # Update data to queue
                    q.put((out))
                    # Check is maximum number of points is reached
                    if self.numpoints>self.maxpoints or self.stop:
                        break
            finally:
                try:
                    task.close()
                except:
                    pass
                
                
    def continous_Nread(self,stop_event,q,sample_rate, Nsamples):
        '''
        Function to read continuously data from DAQ card. Data is read every time 
        callback is triggered. Best function for fast data collection as this is
        Event based.

        Parameters
        ----------


        Parameters
        ----------
        q : multiprocessing queue
            queue to send the data onwards
        stop_event : multiprocessing Event
            event to stop the data aquisition
        sample_rate : int
            Data measurement rate
        Nsamples : int
            amount of samples collected before event is active

        Returns
        -------
        Puts data to queue, format is [time, array(shape = Nchannel x Nsamples)]

        '''
        #!!!
        # Initalize numpy array
        out = np.zeros((len(self.channels), Nsamples))
        # Function that is triggered when desired number of samples is registered
        def every_n_callback(task_handle, every_n_samples_event_type, number_of_samples, callback_data):
            # Create reader
            reader = AnalogMultiChannelReader(self.task.in_stream)
            # Read samples to buffer
            reader.read_many_sample(out, number_of_samples_per_channel=number_of_samples)
            # Put samples to queue
            q.put([perf_counter()-t0,out])
            return 0  # Must return 0 or DAQmx will consider it an error
        # Log starttime
        t0 = perf_counter()
        # Create task
        with nidaqmx.Task() as self.task:
            # Create voltage channels
            for ch in self.channels:
                self.task.ai_channels.add_ai_voltage_chan(ch,min_val=self.range[0], max_val=self.range[1])
        
            # Setting the rate of the Sample Clock and the number of samples to acquire
            self.task.timing.cfg_samp_clk_timing(rate = sample_rate, sample_mode=AcquisitionType.CONTINUOUS, samps_per_chan = Nsamples)
        
            # Register the callback for every N samples acquired
            self.task.register_every_n_samples_acquired_into_buffer_event(Nsamples, every_n_callback)
        
            # Start the task
            self.task.start()
            
            # Stop the data acquisition when stop event is set
            while not stop_event.is_set():
                continue
            self.task.stop()
            print('Data acquisition stopped')


    def continous_Nread_test(self,stop_event,q,sample_rate, Nsamples):
        '''
        Function to test DAQ acquisition without hardware

        '''
        # Initalize numpy array
        out = np.ones((len(self.channels), Nsamples))
        # Log starttime
        t0 = perf_counter()
        # Create test data until stop event is set
        while not stop_event.is_set():
            # Create random array
            rn = 0.2*np.random.rand(len(self.channels), Nsamples)

            q.put([perf_counter()-t0,np.multiply(out,rn)])
            # Delay to slow down the code
            time.sleep(1e-3)
        print('Data acquisition stopped')



    def write_data(self, channel_out, value):
        '''
        Function for writing data in DAQ analog output channels

        Parameters
        ----------
        channel_out : string
            channel to which data is written
        value : float
            value

        Returns
        -------
        None.

        '''
        with nidaqmx.Task() as self.write_task:
            # Set up output channel
            self.write_task.ao_channels.add_ao_voltage_chan(channel_out,max_val=10, min_val=-10)
            self.write_task.start()
            writer = AnalogMultiChannelWriter(self.write_task.in_stream)
            # Read datapoints from DAQ to out array
            writer.write_one_sample(np.array([value]))

                
    def request_data(self, out, sample_rate, N_samples):
        '''
        Function for requesting N_samples from DAQ using NI-DAQmx interface. 
        Not optimal for sequential fast measurements as this method initializes task every time

        Parameters
        ----------
        out : array 
            array for data, size (channels) x (samples)         
        sample_rate : float
            Specifies the sampling rate in samples per channel per second
        N_samples : int
            Specifies the number of samples to acquire or generate for each channel in the task

        Returns
        -------
        None.

        '''
        with nidaqmx.Task() as self.task:
            # Add voltage channels
            for ch in self.channels:
                self.task.ai_channels.add_ai_voltage_chan(ch,min_val=self.range[0], max_val=self.range[1])
            # Setting the rate of the Sample Clock and the number of samples to acquire
            self.task.timing.cfg_samp_clk_timing(sample_rate, source="", sample_mode=AcquisitionType.FINITE, samps_per_chan = N_samples)
            #task.register_done_event(self.callback_method)
            # Initializing new stream reader for the task
            self.task.start()
            reader = AnalogMultiChannelReader(self.task.in_stream)
            # Read datapoints from DAQ to out array
            reader.read_many_sample(data = out,number_of_samples_per_channel =  nidaqmx.constants.READ_ALL_AVAILABLE)
            # callback function
            def callback_method(task_handle=self.task._handle,signal_type=nidaqmx.constants.Signal.SAMPLE_COMPLETE,callback_data=1):
                return 0
            # Register event when sample is finished
            self.task.register_signal_event(nidaqmx.constants.Signal.SAMPLE_COMPLETE, callback_method)
            try:
                self.task.stop()
            except Exception as e:
                print(e)
    
def getChannelNames(device_name):
    '''
    Method to get available physical ai channels of the device

    Returns
    -------
    list
        list of available ai channel names

    '''
    device = nidaqmx.system.device.Device(device_name)
    available_channels = device.ai_physical_chans.channel_names
    print('Available ai channels: ')
    print(available_channels)
    return available_channels  
             


if __name__ == '__main__':
   daq=DAQcontrol(["Dev1/ai1","Dev1/ai2"])
   '''
   filename='D:\\DATA\\AKI\\NIDAQmx\\file4.tdms'
   sample_rate=1e5
   N_samples=10000
   import os
   if os.path.exists(filename):
       os.remove(filename)
   logtask=daq.log_data(sample_rate, N_samples, filename)
   
   '''
   stop_event = mp.Event()
   sample_rate = 5000
   Nsamples = 100
   q = mp.Queue()
   measData = mp.Process(target = daq.continous_Nread,args = (q,stop_event,sample_rate, Nsamples))
   measData.start()
   time.sleep(10)
   stop_event.set()
   
   '''
   N_samples=2
   starttime=time.perf_counter()
   out = np.empty(shape=(len(daq.channels),N_samples))
   for i in range(100):
       daq.request_data(out,1e5,N_samples)
       print(out)
    '''
   '''
   daq=DAQcontrol(["PXI1Slot3/ai1","PXI1Slot3/ai2"])
   #N_buffer=N_samples*2
   sample_rate=1e5
   N_samples=1000
   daq.maxpoints=100
   starttime=time.perf_counter()
   q=Queue()
   
   starttime=time.perf_counter()
   daq_th = threading.Thread(target=daq.collect_data, args=( q, sample_rate, N_samples))
   daq_th.Daemon=True
   daq_th.start()

   data=[]
   k=0
   try:
       while daq_th.isAlive():
           try:
               x = q.get_nowait()
               data.append(x)
               t = time.perf_counter()
               if q.qsize()>0:
                   print('Queue filling: ',q.qsize())
           except Empty:
               pass
           else:
                if k%10==0:
                    plt.plot(t-starttime,np.average(x[0]),'r.')
                    plt.plot(t-starttime,np.average(x[1]),'b.')
                    plt.pause(0.001)
           k+=1
   finally:
       daq.Stop()
   daq_th.join()
   '''