import os.path
import numpy as np
import math
from pymmcore_plus import CMMCorePlus
import cv2

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

    def zoomIn(self, img, percentage:int):
        """Zooms the image in by percentage. A 0 percent zoom
        indicates we are using the original resolution of the camera.
        A 100 percent zoom produces a 0x0 image.

        :param img: image to zoom in on
        :type img: 2d numpy array
        :param percentage: amount to zoom in by
        :type percentage: integer
        """
        originalHeight, originalWidth = img.shape

        newH = originalHeight -  int(originalHeight * (percentage / 100))
        newW = originalWidth -  int(originalWidth * (percentage / 100))

        return img[originalHeight // 2 - newH // 2 : originalHeight // 2 + newH // 2, 
                    originalWidth // 2 - newW // 2 : originalWidth  // 2 + newW // 2]

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

        # specifying out=img keeps these operations in place, no copying to new output
        np.clip(img, 0, 2**(16-gainFactor)-1, out=img)
        np.multiply(img, np.array(self.gain).astype(np.float64), out=img, casting='unsafe')
        
        # clip below necessary only for imagetk
        # np.clip((((img) / (2**16-1)) * 255).astype(np.uint8), 0, 255, out=img)

    def drawCross(self, img, crossColor=255, crossWidth=5) -> np.array:
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
        # rv, cv, valv = line_aa( numRows // 2 - crossLen // 2 , numCols // 2, numRows // 2 + crossLen // 2 , numCols // 2)
        # rh, ch, valh = line_aa(numRows // 2, 0 , numRows // 2, numCols - 1)

        cv2.line(img, (0, numRows//2), (numCols, numRows//2), crossColor, crossWidth)
        cv2.line(img, (numCols//2, 0), (numCols//2, numRows), crossColor, crossWidth)

        # img[rv,cv] = valv * crossColor
        # img[rh,ch] = valh * crossColor
        # return img