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
    def __init__(self):
        """
        Instantiates a camera with the given config file
        Does not actually connect to the camera

        :raises ValueError: if any files (from micromanager)
        related to the specific Camera don't exist
        """

        # all cameras share this
        self.mmPath = "C:\Program Files\Micro-Manager-2.0"
        pass

    @abc.abstractmethod
    def connect(self) -> None:
        """
        Connect to the camera via micromanager
        Does nothing if already connected

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
        pass

    @abc.abstractmethod
    def isConencted(self) -> bool:
        """
        Returns whether or not the camera
        object is connected to the physical
        camera

        :rtype: bool
        """
        pass

    @abc.abstractmethod
    def getNextFrame(self) -> numpy.ndarray | None:
        """
        Reads the next available frame from the camera

        :return: A numpy.ndarray of the raw
            image, or None if the camera
            is not in sequenceAcquisition mode
        :rtype: numpy.ndarray | None
        """
        pass

    @abc.abstractmethod
    def setExposure(self, exposure: float) -> None:
        """
        Sets the camera exposure (in ms)
        Exposures <0 will be clipped to 0

        :param exposure: exposure (ms)
        :type exposure: float
        """
        pass

    @abc.abstractmethod
    def getNumWaitingFrames(self):
        """
        Return the number of images stored 
        internally

        Note: camera storage is circular,
        meaning the number of stored images is
        not limitless, and restarts from 0 after
        exceeding a certain amount.
        """
        pass

    @abc.abstractmethod
    def reset(self) -> None:
        """
        Resets the connection to micromanager,
        disconnecting device
        """
        pass
