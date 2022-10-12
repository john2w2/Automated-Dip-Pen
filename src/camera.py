import pymmcore
import os.path
import numpy as np
import math
from pymmcore_plus import CMMCorePlus
from time import sleep

from skimage.transform import resize # necessary if we want to resize without opencv
from skimage.draw import line_aa # can draw lines with this instead of cv

class Camera:
    def __init__(self, configPath="Coolsnap.cfg"):
        mm_dir = "C:\Program Files\Micro-Manager-2.0"
        self.mmc = CMMCorePlus.instance(mm_path=mm_dir)
        # self.mmc = pymmcore.CMMCore()
        self.mmc.loadSystemConfiguration(os.path.join(mm_dir, configPath))
        # self.mmc.setDeviceAdapterSearchPaths([mm_dir])
        # self.mmc.loadSystemConfiguration(os.path.join(mm_dir, "Coolsnap.cfg"))
        # self.mmc.loadSystemConfiguration(os.path.join(mm_dir, configPath))
        # self.mmc.loadSystemConfiguration(os.path.join(mm_dir, "MMConfig_ham.cfg"))
        self.mmc.setExposure(300)
        self.rMin = None
        self.rMax = None
        self.gain = 20 # default gain of 20 (max) TODO: change from 20

        self.mmc.startContinuousSequenceAcquisition()

    # return ndarray
    # NOTE: will be deprecated
    def getImage(self, resizeImg=True, crop=False, scale=True):
        # self.mmc.snapImage()
        # img = self.mmc.getImage()
        # img = self.mmc.snap()
        while (self.mmc.getRemainingImageCount() == 0):
            sleep(0.05)
        img = self.mmc.getLastImage()

        if crop: img = self.cropToChannel(img) # crop before resizing so quality remains good(ish)
        if resizeImg: img = (resize(img, (401, 601), preserve_range=True))
        if scale: img = self.scaleImage(img)
        return img

    def cropToChannel(self, img):
        numR, numC = img.shape
        img = img[numR // 2- 50: numR // 2 + 50, numC // 2 - 75: numC // 2 + 75]
        return img

    def setExposure(self, exposure: int):
        """Sets the camera exposure (in ms)

        :param exposure: exposure (ms)
        :type exposure: int
        """

        self.mmc.setExposure(exposure)

    def setGain(self, gain: float):
        """Sets the gain of the camera

        :param gain: desired gain. Must be in the interval [0.5, 4]
        :type gain: float
        """

        if gain < 0.5 or gain > 4:
            raise ValueError("Desired gain does not fall between 0.5 and 4")

        self.gain = gain
    
    def scaleImage(self, img):
        """Scales the iamge by previously set gain (default to 4)
        """
        gainFactor = math.ceil(np.log10(self.gain) / np.log10(2))
        img = np.clip(img, 0, 2**(16-gainFactor)-1)
        img = img * self.gain

        # convert to 8-bit integer because that's what ImageTk wants for some reason
        img = np.clip((((img) / (2**16-1)) * 255).astype(np.uint8), 0, 255)
        return img

    def drawCross(self, img) -> np.array:
        """Draws a cross on a copy img, not modifying the original image 

        :param img: the image to draw a cross on
        :type img: m x n matrix
        :return: m x n matrix with a cross drawn on the center
        :rtype: np.array
        """
        imCopy = np.matrix.copy(img)
        numRows = img.shape[0]
        numCols = img.shape[1]

        # make cross same length along each axis
        crossLen = min(numRows // 5, numCols // 5)
        rv, cv, valv = line_aa( numRows // 2 - crossLen // 2 , numCols // 2, numRows // 2 + crossLen // 2 , numCols // 2)
        rh, ch, valh = line_aa(numRows // 2, 0 , numRows // 2, numCols - 1)

        imCopy[rv,cv] = valv * 255
        imCopy[rh,ch] = valh * 255
        return imCopy