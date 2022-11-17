import abc
import numpy


class Camera(abc.ABC):
    """
    An Interface for a camera. Cameras connect
    to a microscope camera via micromanager and
    are responsible for acquiring sequences of
    images and providing the client with those
    images

    To be able to retrieve images from the camera,
    it must be running sequence acquisition from
    a call to `startAcquisition()`

    A camera takes complete control over the
    micromanager program, meaning it is not
    possible to run multiple cameras in parallel
    at this time.
    """

    @abc.abstractmethod
    def __init__(self, configName: str, mmPath: str):
        """
        Instantiates a camera with the given config file
        Does not actually connect to the camera

        :param configName: name of the *.cfg file
            for the current Camera
        :type configPath: str

        :param mmPath: absolute path to the micromanager
            directory
            (e.g. "C:\\Program Files\\Micro-Manager-2.0")
        :type mmPath: str
        :raises ValueError: if the mmPath directory or
            configName file don't exist
        """
        pass

    @abc.abstractmethod
    def connect(self) -> None:
        """
        Connect to the camera via micromanager
        :raises ConnectionError: if unable to
            connect to the camera
        """
        pass

    @abc.abstractmethod
    def startAcquisition(self) -> None:
        """
        Begin continuously snapping images, storing them
        in the camera.

        Does nothing if the camera is not connected
        """
        pass

    @abc.abstractmethod
    def stopAcquisition(self) -> None:
        """
        Stop snapping images

        Does nothing if the camera is not connected
        """
        pass

    @abc.abstractmethod
    def isAcquiring(self) -> bool:
        """
        Returns whether or not the is in sequence
        acquisition mode

        :rtype: bool
        """

    @abc.abstractmethod
    def isConencted(self) -> bool:
        """
        Returns whether or not the camera
        object is connected to the physical
        camera

        :rtype: bool
        """

    @abc.abstractmethod
    def getNextFrame(self) -> numpy.ndarray | None:
        """
        Reads the next available frame from the camera

        :return: A numpy.ndarray of the raw
            image, or None if the camera
            is not in sequenceAcquisition mode
        :rtype: numpy.ndarray | None
        """

    @abc.abstractmethod
    def getNumWaitingFrames(self):
        """
        Return the number
        of images stored internally
        Note: camera storage is circular,
        meaning the number of stored images is
        not limitless, and restarts
        """
        pass

    @abc.abstractmethod
    def reset(self) -> None:
        """
        Resets the connection to micromanager,
        disconnecting device
        """
        pass
