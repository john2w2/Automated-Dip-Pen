from math import ceil
import numpy as np
import cv2
from deviceInterfaces.camera import Camera
from PIL import Image
import datetime
import os

"""
A collection of utility functions for
camera-acquired images
"""

def crop_to_channel(img):
    numR, numC = img.shape
    return img[ numR // 2- 50: numR // 2 + 50, 
                numC // 2 - 75: numC // 2 + 75]

def zoom_by_percentage(img: np.ndarray, percentage: int):
    """
    Zooms the image in by percentage. A 0 percent zoom
    indicates we are using the original resolution of the camera.
    A 100 percent zoom produces a 0x0 image.

    :param img: image to zoom in on
    :type img: 2d numpy array
    :param percentage: amount to zoom in by
    :type percentage: integer
    """
    originalHeight, originalWidth = img.shape

    newH: int = originalHeight -  int(originalHeight * (percentage / 100))
    newW: int = originalWidth -  int(originalWidth * (percentage / 100))

    return img[originalHeight // 2 - newH // 2 : originalHeight // 2 + newH // 2, 
                originalWidth // 2 - newW // 2 : originalWidth  // 2 + newW // 2]

def apply_gain(img: np.ndarray, gain: int):
    """
    Scales the pixel values in image by gain

    This happens in-place, meaning the original
    image is modified

    :param img: image to apply gain to
    :type img: np.ndarray
    :param gain: scalar to multiply each pixel by
    :type gain: int
    """
    # indicates the max number of additional bits
    # required by a pixel scaled by gain
    gainFactor = ceil(np.log10(gain) / np.log10(2))

    # limit pixel brightnesses to ensure multiplying
    # will not overflow
    np.clip(img, 0, 2**(16-gainFactor)-1, out=img)
    np.multiply(img, np.array(gain)
        .astype(np.float64), out=img, casting='unsafe')
    
    # since we specified out=img in each np call, our 
    # original image has been modified

def draw_cross(img, crossColor=255, crossWidth=5) -> np.array:
    """
    Draws a cross on image, modifying the original image 
    rather than copying it 

    :param img: the image to draw a cross on
    :type img: m x n matrix
    """

    numRows = img.shape[0]
    numCols = img.shape[1]

    cv2.line(img, (0, numRows//2), (numCols, numRows//2), crossColor, crossWidth)
    cv2.line(img, (numCols//2, 0), (numCols//2, numRows), crossColor, crossWidth)

def save_image_from_camera(camera: Camera, 
    gain:int,
    fileName:str,
    parent_dir: str = "C:\\Users\\19199\\Desktop\\automated-sca\\development\\ValueStorage\\images") -> None:
    if camera.is_acquiring():
        im = camera.get_next_frame()
        apply_gain(im, gain=gain)
        pilim = Image.fromarray(im)
        # current_time = get_date_str(date_as_dir=False)
        # file_name = current_time + ".tiff"
        # file_path = os.path.join(parent_dir, file_name)
        if len(fileName.split(".tiff")) != 2:
            fileName += ".tiff"
        pilim.save(fileName)
    else:
        raise ValueError("Camera is not acquiring, cannot save image")
        
def get_date_str(date_as_dir: bool = True) -> str:
    currentTime = datetime.datetime.now()
    if not date_as_dir:
        currentTimeRounded: str = currentTime.__str__().split(".")[0]
        currentTimeFormatted = currentTimeRounded.replace("-", "_").replace(" ", "_").replace(":", "_")
        return currentTimeFormatted
    else:
        directory: str = currentTime.date().__str__().replace("-", "_")
        time: str = currentTime.time().__str__().split(".")[0].replace(":", "_")
        return directory + "\\" + time