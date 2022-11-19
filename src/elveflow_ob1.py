import sys
import pathlib
import os
from deviceInterfaces.pressure_system import PressureSystem

# sys.path.insert(1,"C:\\Users\\19199\\Desktop\\kyler v\\Flow Controller\\python_64")
# sys.path.insert(1,"C:\\Users\\19199\\Desktop\\kyler v\\Flow Controller\\python_64\\DLL64")
sys.path.insert(1, 'C:\\Users\\19199\\Desktop\\automated-sca\\flow_controller\\python_64')
sys.path.insert(1, 'C:\\Users\\19199\\Desktop\\automated-sca\\flow_controller\\python_64\\DLL64')

from Elveflow64 import *
from ctypes import *


class ElveflowOB1(PressureSystem):
    """
    Wrapper for OB1 Pressure Controller from Elveflow. 4 channel device
    Channels 1-2 are rated for 0 to 2000 mbar
    Channels 3-4 are rated for -1000 to 1000 mbar
    Almost all methods will return error codes, read through the Elveflow SDK for more info on that if you want

    NOTE: despite this being a mult-channel device, we will only control one 
    channel (DEF_CHANNEL)
    """
    def __init__(self, calibrate: bool=False):
        """
        Constructor for OB1
        :param calibrate: Set true to run calibration at startup. Calibration should be done at first time startup.
                            Calibration data will be saved to a certain path, but feel free to modify. 
                            Further testing should be done to see if calibration has to be done every time the device
                            starts up. As of now, it seems like it would be a good idea to do it at every startup.
        """
        self.DEF_CHANNEL: int = 3 # the default channel to control
        # this device's unique id, used when connecting to it
        self.NI_ID = "01CF6A56"
        # change file path
        parentDir = pathlib.Path(__file__).parent.resolve()
        self.cal_path = os.path.join(parentDir, 'calibrationFiles', f'{self.NI_ID}.txt')
        self.instr_ID = c_int32()
        # initialize device. "2, 2, 4, 4" defines channel regulator types, so 2 is the 0/2000 reg and 4 is the -1000/1000 reg
        self.error = OB1_Initialization(self.NI_ID.encode("ascii"), 2, 2, 4, 4, byref(self.instr_ID))
        if self.error != 0:
            print(self.error)
            print(self.NI_ID)
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

    def calibrate(self) -> None:
        """
        initiate calibration.
        """
        print("Calibrating...")
        error = OB1_Calib(self.instr_ID.value, self.calibration_array, 1000)
        Elveflow_Calibration_Save(self.cal_path.encode('ascii'), byref(self.calibration_array), 1000)
        print("Calibration Completed")
        # return error

    def set_pressure(self, pressure: float) -> None:
        """
        Sets the pressure of the default channel
        :param pressure: set pressure in mbar
        :return: error code
        """
        error = OB1_Set_Press(
            self.instr_ID.value,
            self.DEF_CHANNEL,
            pressure,
            byref(self.calibration_array),
            1000
            )
        # return error
    
    def set_pressure_on_channel(self, pressure:float, channel: int):
        """
        Sets the pressure for a specific channel
        only used internally

        :param pressure: pressure (mbar)
        :type pressure: float
        :param channel: channel to set pressure on
        :type channel: int
        """
        OB1_Set_Press(
            self.instr_ID.value,
            channel,
            pressure,
            byref(self.calibration_array),
            1000
            )

    def reset_pressure(self) -> None:
        """
        set all channel pressures to 0
        """
        self.set_pressure_on_channel(0, 1)
        self.set_pressure_on_channel(0, 2)
        self.set_pressure_on_channel(0, 3)
        self.set_pressure_on_channel(0, 4)

    def get_pressure(self) -> float:
        """
        gets pressure (in mbar) of the default
        channel
        """
        pressure = c_double()
        OB1_Get_Press(
            self.instr_ID.value,
            self.DEF_CHANNEL,
            1,
            byref(self.calibration_array),
            byref(pressure),
            1000
            )
        return pressure.value

    def close(self):
        """
        closes connection to OB1, sets all output channels to 0
        :return: error code
        """
        self.reset_pressure()
        error = OB1_Destructor(self.instr_ID.value)
        return error

