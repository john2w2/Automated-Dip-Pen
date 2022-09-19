from audioop import cross
import pymmcore
import os.path
import numpy as np

from skimage.transform import resize # necessary if we want to resize without opencv
from skimage.draw import line_aa # can draw lines with this instead of cv

class Camera:
    def __init__(self):
        mm_dir = "C:\Program Files\Micro-Manager-2.0"
        self.mmc = pymmcore.CMMCore()
        self.mmc.setDeviceAdapterSearchPaths([mm_dir])
        self.mmc.loadSystemConfiguration(os.path.join(mm_dir, "Coolsnap.cfg"))
        self.rMin = None
        self.rMax = None

    # return ndarray
    def getImage(self, resizeImg=True, contrast=True):
        self.mmc.snapImage()
        img = self.mmc.getImage()
        if contrast: img = self.contrastImage(img)
        if resizeImg: img = (resize(img, (401, 601), preserve_range=True))
        return img

    def contrastImage(self, img):
        """Increase constrast in image

        :param img: Image taken by camera
        :type img: ndarray
        :return: Processed image
        :rtype: ndarray
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
        rh, ch, valh = line_aa(numRows // 2, numCols // 2 - crossLen //2, numRows // 2, numCols // 2 + crossLen // 2)

        imCopy[rv,cv] = valv * 255
        imCopy[rh,ch] = valh * 255
        return imCopy