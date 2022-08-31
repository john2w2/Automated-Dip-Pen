# TODO: algorithms here are for calibration, have not decided where they should go yet


import matplotlib.pyplot as plt
from camera import Camera
from stage import Stage
from plate import Plate
from chip import Chip



def calibFirstWellPos():
    """Get position (in stage steps) of first well's center under camera

    Explanation:
        We want to find the center of the well under the camera
        Most of the time, you will not be able to view the entire well under
        the camera

        We can assume each well is a perfect circle
        A right triangle with all 3 endpoints on the circle boundary will
        have one of its sides go through the center, with length = diameter

    Procedure:
        1. Fill first well- (1, 1) with 700 microliters of fluorescent buffer
        2. Locate top left of first well under camera. Well should be bright gray/white, everything else black
        3. Place center of cross just left of the fluorescent well, still in the black region

    :return: Coordinates of first well center under camera (in stage steps)
    :rtype: (int, int)
    """
    c = Chip()
    p = Plate()
    s = Stage(p, c)
    cam = Camera()


    img = cam.getImage()
    numRows, numCols = img.shape
    blackCeil = 20 # any pixel with value < blackCeil is black, part of wall

    # Move to point A
    # move right until you are touching the boundary
    # (move right by moving stage left)

    centerPixel = img[numRows//2, numCols//2]
    while centerPixel < blackCeil:
        s.moveXInUM(-2)
        img = cam.getImage()
        centerPixel = img[numRows//2, numCols//2]

    pointA = s.getStageXY()

    # Move to point B:
    # We're now looking at some point inside the well, centerPixel >= blackCeil
    while centerPixel >= blackCeil and img[numRows//2, numCols//2+1] >= blackCeil:
        s.moveXInUM(-30)
        img = cam.getImage()
        centerPixel = img[numRows//2, numCols//2]

    # microadjustment
    while centerPixel < blackCeil:
        s.moveXInUM(2)
        img = cam.getImage()
        centerPixel = img[numRows//2, numCols//2]

    pointB = s.getStageXY()

    # For 96-well plate, takes around 42s

    # Move to C
    while centerPixel >= blackCeil and img[numRows//2+1, numCols//2] >=blackCeil:
        s.moveYInUM(-30)
        img = cam.getImage()
        centerPixel = img[numRows//2, numCols//2]
    while centerPixel < blackCeil:
        s.moveYInUM(2)
        img = cam.getImage()
        centerPixel = img[numRows//2, numCols//2]

    pointC = s.getStageXY()

    centerX = pointA[0] + (pointC[0] - pointA[0]) // 2
    centerY = pointA[1] + (pointC[1] - pointA[1]) // 2

    s.close()

    return (centerX, centerY)

