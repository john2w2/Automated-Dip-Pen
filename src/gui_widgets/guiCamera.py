import pymmcore
import os.path
import cv2 as cv
import numpy as np

# TODO: remove cv2 dependency

class GUICamera:
    def __init__(self):
        mm_dir = "C:\Program Files\Micro-Manager-2.0"
        self.mmc = pymmcore.CMMCore()
        self.mmc.setDeviceAdapterSearchPaths([mm_dir])
        self.mmc.loadSystemConfiguration(os.path.join(mm_dir, "Coolsnap.cfg"))
        self.rMin = None
        self.rMax = None

    def getImage(self):
        self.mmc.snapImage()
        img = self.mmc.getImage()
        img = self.mapImage(img)
        img = (cv.resize(img, (img.shape[1] // 2, img.shape[0] // 2))) 
        return img

    def mapImage(self, img):
        """
        maps image values to 0-255 such that min of image becomes 0 and max of image becomes 255
        Works well when there is a light source, but image is grainy when the image is really dark
        """

        if (self.rMin == None):
            self.rMin = np.min(img)
            self.rMax = np.max(img)
        else:
            # compute rolling average of min (auto brightness effect)
            # this is bad, but not sure how to handle consistently making sure image is bright quickly
            # tweak scalars to change how quickly brightness adjusts (must sum to 1.0)
            self.rMin = self.rMin * 0.9 + 0.1 * np.min(img)
            self.rMax = self.rMax * 0.9 + 0.1 * np.max(img)
        return np.clip((((img - self.rMin) / (self.rMax - self.rMin)) * 255).astype(np.uint8), 0, 255)

    def drawCross(self, img):
        numRows = img.shape[0]
        numCol = img.shape[1]
        cv.line(img, (3 * (numCol // 8), numRows//2), (5 * (numCol // 8), numRows//2), 255, thickness=1) # TODO: color value?
        cv.line(img, (numCol//2,3 * (numRows // 8)), (numCol//2, 5 * (numRows // 8)), 255, thickness=1)
    