import abc  # for making this an interface


class PressureSystem(abc.ABC):
    """
    An interface for a pressure system
    Pressure systems connect to a device
    that is able to control the pressure 
    of the printer head. 

    A pressure system has one or more 'channels',
    which independently apply pressure to whatever
    the channel is connected to

    """

    @abc.abstractmethod
    def __init__(self, calibrate: bool=False):
        """
        Connects to the pressure system,
        optionally calibrating it 

        :param calibrate: _description_, defaults to True
        :type calibrate: bool, optional
        :raises ValueError: If no saved calibration
            file exists and calibrate = False
        """

    @abc.abstractmethod
    def calibrate(self) -> None:
        """
        (re)Calibrates the pressure system.
        This may take a while
        """

    @abc.abstractmethod
    def set_pressure(self, pressure: float, channel: int = 0) -> None:
        """
        Sets the pressure to the desired pressure 

        :param pressure: Desired pressure (measured in mbar)
            for the pressure system to apply
        :type pressure: float 
        :param channel: Desired channel of the pressure
            system to apply the pressure to
        :type channel: int 
        """

    @abc.abstractmethod
    def reset_pressure(self) -> None:
        """
        Sets the pressure to 0 on all channels
        """

    @abc.abstractmethod
    def get_pressure(self, channel: int=0) -> float:
        """
        Gets the pressure for the given channel.

        :param channel: Channel to read pressure of, defaults to 0
        :type channel: int, optional
        :return: pressure of the given channel
        :rtype: float
        """

    @abc.abstractmethod
    def close(self):
        """
        Closes the connection to the pressure system
        """

    def __del__(self):
        self.close()
