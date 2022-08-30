import sys
import pathlib
import os

# sys.path.insert(1,"C:\\Users\\19199\\Desktop\\kyler v\\Flow Controller\\python_64")
# sys.path.insert(1,"C:\\Users\\19199\\Desktop\\kyler v\\Flow Controller\\python_64\\DLL64")
sys.path.insert(1, 'C:\\Users\\19199\\Desktop\\automated-microscope\\code_hierarchy_draft\\flow_controller\\python_64')
sys.path.insert(1, 'C:\\Users\\19199\\Desktop\\automated-microscope\\code_hierarchy_draft\\flow_controller\\python_64\\DLL64')

from Elveflow64 import *
from ctypes import *


class OB1:
    """
    Wrapper for OB1 Pressure Controller from Elveflow. 4 channel device
    Channels 1-2 are rated for 0 to 2000 mbar
    Channels 3-4 are rated for -1000 to 1000 mbar
    Almost all methods will return error codes, read through the Elveflow SDK for more info on that if you want
    """
    def __init__(self,NI_ID="01CF6A56",calibrate=False,cal_path=f"C:\\Users\\19199\\Desktop\\automated-microscope\\code_hierarchy_draft\\flow_controller\\calibration"):
        """
        Constructor for OB1
        :param NI_ID: The device ID for OB1 found in the NI MAX software.
        :param calibrate: Set true to run calibration at startup. Calibration should be done at first time startup.
                            Calibration data will be saved to a certain path, but feel free to modify. 
                            Further testing should be done to see if calibration has to be done every time the device
                            starts up. As of now, it seems like it would be a good idea to do it at every startup.
        :param cal_path: path to save calibration data to
        """
        self.NI_ID = NI_ID
        # change file path
        parentDir = pathlib.Path(__file__).parent.resolve()
        self.cal_path = os.path.join(parentDir, 'calibration', f'{self.NI_ID}.txt')
        self.instr_ID = c_int32()
        # initialize device. "2, 2, 4, 4" defines channel regulator types, so 2 is the 0/2000 reg and 4 is the -1000/1000 reg
        self.error = OB1_Initialization(self.NI_ID.encode("ascii"), 2, 2, 4, 4, byref(self.instr_ID))
        if self.error != 0:
            print(self.error)
            print(NI_ID)
            print("Device connection failed")
            return None
        else:
            print("Device connection made")
        self.calibration_array = (c_double*1000)()
        if calibrate:
            # run calibration and save to path
            self.calibrate()
        else:
            # load previous calibration data
            try:
                Elveflow_Calibration_Load(self.cal_path.encode('ascii'),byref(self.calibration_array),1000)
            except FileNotFoundError:
                print('fix path')
        self.reset_pressure()

    def calibrate(self,save=True):
        """
        initiate calibration.
        """
        print("Calibrating...")
        error = OB1_Calib(self.instr_ID.value, self.calibration_array, 1000)
        if save:
            Elveflow_Calibration_Save(self.cal_path.encode('ascii'), byref(self.calibration_array), 1000)
        print("Calibration Completed")
        return error

    def set_pressure(self,channel,pressure):
        """
        sets pressure to channel
        :param channel: which channel (1-4) to set pressure for. Channels 1-2 handle 0 to 2000 mbar, while
                        channels 3-4 can handle -1000 to 1000 mbar
        :param pressure: set pressure in mbar
        :return: error code
        """
        error = OB1_Set_Press(self.instr_ID.value, channel, pressure, byref(self.calibration_array), 1000)
        return error
    
    def reset_pressure(self):
        """
        set all channel pressures to 0
        """
        self.set_pressure(1,0)
        self.set_pressure(2,0)
        self.set_pressure(3,0)
        self.set_pressure(4,0)

    def get_pressure(self,channel):
        """
        gets pressure of channel in mbar
        :param channel: select channel
        :return: channel pressure in mbar
        """
        pressure = c_double()
        OB1_Get_Press(self.instr_ID.value, channel, 1, byref(self.calibration_array), byref(pressure), 1000)
        return pressure.value

    def close(self):
        """
        closes connection to OB1, sets all output channels to 0
        :return: error code
        """
        self.reset_pressure()
        error = OB1_Destructor(self.instr_ID.value)
        return error

