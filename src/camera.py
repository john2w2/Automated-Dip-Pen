import os.path
import numpy as np
import math
from pymmcore_plus import CMMCorePlus

from skimage.draw import line_aa # can draw lines with this instead of cv

class Camera:
    def __init__(self, configPath="Coolsnap.cfg"):
        # configPath = "MMConfig_ham.cfg"
        mm_dir = "C:\Program Files\Micro-Manager-2.0"
        self.mmc = CMMCorePlus.instance(mm_path=mm_dir)

        try:
            self.mmc.loadSystemConfiguration(os.path.join(mm_dir, configPath))
        except:
            self.mmc.reset()
            raise ValueError("please make sure camera is plugged in")
        
        self.rMin = None
        self.rMax = None
        self.gain = 20 # default gain of 20 (max) TODO: change from 20

        self.snapping = False # indicates whether or not continuous acquisition is running

    def startAcquisition(self):
        self.mmc.startContinuousSequenceAcquisition() # start reading a bunch of images
        self.snapping = True

    def stopAcquisition(self):
        if self.snapping:
            self.mmc.stopSequenceAcquisition()

        self.snapping = False

    def waitingImages(self):
        return self.mmc.getRemainingImageCount()

    def getNextFrame(self):
        """Gets the next image in the video feed
        Assumes there is a frame ready to be read

        :return: The next frame
        :rtype: 2d array
        """
        return self.mmc.getLastImage()

    def reset(self):
        self.mmc.reset()

    def cropToChannel(self, img):
        # TODO: zoom may be too aggressive with new camera
        numR, numC = img.shape
        img = img[numR // 2- 50: numR // 2 + 50, numC // 2 - 75: numC // 2 + 75]
        return img

    def setExposure(self, exposure: float):
        """Sets the camera exposure (in ms)

        :param exposure: exposure (ms)
        :type exposure: float
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
        """Scales the image by previously set gain (default to 4)
        """
        gainFactor = math.ceil(np.log10(self.gain) / np.log10(2))
        img = np.clip(img, 0, 2**(16-gainFactor)-1)
        img = img * self.gain

        # convert to 8-bit integer because that's what ImageTk wants for some reason
        img = np.clip((((img) / (2**16-1)) * 255).astype(np.uint8), 0, 255)
        return img

    def drawCross(self, img, crossColor=255) -> np.array:
        """Draws a cross on image, modifying the original image 
        rather than copying it 
        (not copying to make this run much faster)

        :param img: the image to draw a cross on
        :type img: m x n matrix
        """

        numRows = img.shape[0]
        numCols = img.shape[1]

        # make cross same length along each axis
        crossLen = min(numRows // 5, numCols // 5)
        rv, cv, valv = line_aa( numRows // 2 - crossLen // 2 , numCols // 2, numRows // 2 + crossLen // 2 , numCols // 2)
        rh, ch, valh = line_aa(numRows // 2, 0 , numRows // 2, numCols - 1)

        img[rv,cv] = valv * crossColor
        img[rh,ch] = valh * crossColor
        # return img