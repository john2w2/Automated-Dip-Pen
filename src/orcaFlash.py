import numpy as np
import sys
from pymmcore_plus import CMMCorePlus

from deviceInterfaces.camera import Camera

# exposure that the camera should have when it 
# first turns on
DEFAULT_EXPOSURE: float = 33.3 

class OrcaFlashV2(Camera):
    """
    A Hamamatsu Orca Flash V2 camera
    for microscope imaging

    :param Camera: Interface from which this 
        inherits its methods
    """
    def __init__(self):
        self.mm_path = "C:\\Program Files\\Micro-Manager-2.0"
        
        # path to config file 
        self.configPath = "MMConfig_ham.cfg"

        # indicates whether or not continuous acquisition is running
        self.snapping: bool = False

        self.connected: bool = False

        # to be connected to later
        self.mmc = None

    def connect(self) -> None:
        # Get an instance of mmc
        self.mmc = CMMCorePlus.instance(mm_path=self.mm_path)

        try:
            self.mmc.loadSystemConfiguration(fileName=self.configPath)
            self.mmc.setExposure(DEFAULT_EXPOSURE)
            self.connected: bool = True
        except Exception as e:
            raise e

    def start_acquisition(self) -> None:
        if not self.snapping:
            self.mmc.startContinuousSequenceAcquisition()
            self.snapping: bool = True

    def stop_acquisition(self) -> None:
        if self.snapping:
            self.mmc.stopSequenceAcquisition()

        self.snapping: bool = False

    def is_acquiring(self) -> bool:
        return self.snapping

    def is_connected(self) -> bool:
        return self.connected

    def get_next_frame(self) -> np.ndarray | None:
        return self.mmc.getLastImage()

    def set_exposure(self, exposure: float) -> None:
        if exposure < 0.0:
            exposure = 0.0

        self.mmc.setExposure(exposure)

    def get_num_waiting_frames(self):
        return self.mmc.getRemainingImageCount()

    def reset(self):
        self.mmc.reset()
        self.connected = False

    def __del__(self):
        # stop acquisition (if acquiring)
        if self.snapping:
            self.stop_acquisition()
        # reset mmc
        if self.connected:
            self.reset()
        print("[INFO]: cam object deleted", file=sys.stderr)
