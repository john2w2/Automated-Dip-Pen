import serial
import string
import os
import pathlib

from plate import *
from chip import *


class Stage:
    """
    This class represents the microscope stage and attached devices (well plate and chip)

    Methods in this class enable required stage movements for the rest of the system, such as
    moving to a certain well.

    :param plate: Well Plate used for experimentation
    :type plate: class:`plate.Plate`
    :param chip: Chip used for experimentation
    :type chip: class:`chip.Chip`
    :param port: Name of serial port
    :type port: str, optional
    :param baudrate: Max rate at which information transferred, (in bits/s)
    :type baudrate: int, optional
    :param timeout: Timeout for serial read() (in seconds)
    :type timeout: float, optional
    :param stepSize: Distance (in um) a single motor step will move the stage
    :type stepSize: float, optional

    """

    def __init__(self, plate: Plate, chip: Chip, priorController: serial.Serial, stepSize=0.04):
        """Constructor
        """
        self.ser = priorController
        self.plate = plate
        self.chip = chip

        self.loadPrevOffset()
        self.loadPrevFirstChan()
        self.loadPrevFirstWellPos()
        # TODO: load previously saved first well cam position

        self.stepSize = stepSize

        # Derived Fields:

        # Distance (in motor steps) between centers of 2 adjacent channels
        self.chanStepSize = (self.chip.chanGapWidth +
                             self.chip.chanWidth) / self.stepSize
        # Distance (in motor steps) between centers of 2 adjacent wells
        self.wellStepSize = self.plate.diam / self.stepSize

        # NOTE: we used to have self.plateInitX, plateInitY
        # We should standardize that initial reference well is A1, since there is no guarantee which well plate is being used
        # At least we know for any well plate, A1 exists

    def calibPrinterOffset(self, offsetX: int, offsetY: int):
        """Saves the printer offset values

        Printer offset = (offsetX, offsetY) = relative distance to move from point A to point B
        A = location of fiducial marker under camera view
        B = location of fiducial marker under printer head

        Offset values come from GUI calibration method

        :param offsetX: Distance (in steps) stage has to move to put first
            channel under printer head, starting from first channel
            being focused on cross of camera (along x axis)
            offsetX = printerDropX - focusedDropX
        :type offsetX: int
        :param offsetY: Distance (in steps) stage has to move to put first
            channel under printer head, starting from first channel
            being focused on cross of camera (along y axis)
            offsetY = printerDropY - focusedDropY
        :type offsetY: int
        """
        self.pen_offset_xy = [self.fiducialCamPos - self.penPos for self.fiducialCamPos, self.penPos in zip(self.fiducialCamPos, self.penPos)]
        offsetX = self.pen_offset_xy[0]
        offsetY = self.pen_offset_xy[1]
        self.saveNewOffset(offsetX, offsetY)

    def calibOrigin(self):
        """Define origin for stage

        User moves the stage (using joystick) to bottom right, then redefine that position as origin
        """
        # NOTE: Since (0, 0) is bottom right, stage up => y decreases, stage left => x decreases

        # self.writeRead("G,0,0", isMoveCmd=True) # Move to origin
        # NOTE: now, have user use joystick to move stage to real origin
        self.writeRead("P,0,0,0")  # Redefine this location as origin

    def calibFirstWellCamPos(self):
        # TODO: can we call self.getStageXY() here?
        """Save stage coordinates for well A1 when user moves well A1 under the pen

        :param stagePos: Stage coordinates for location of first well under pen
        :type stagePos: tuple
        """
        self.firstWellCamPos = self.getStageXY()  # Stage coordinates for location of first well
        self.saveNewFirstWellPos(stagePos=self.getStageXY())
        # Stage coordinates for first well under printer head
        # self.firstWellPos = (
        #     stagePos[0]+self.printerOffset[0], stagePos[1]+self.printerOffset[1])

    def calibFirstChannelCamPos(self):
        """Calibrate location of first channel under the camera

        TODO: this is a calibration function, possibly move
        """
        stagePos = self.getStageXY()  # Stage coordinates for location of first channel under camera
        self.firstChannelCamPos = tuple(stagePos)
        self.saveNewFirstChannel(stagePos=stagePos)
        # return stagePos
        # self.firstChannelPos = (
        #     stagePos[0]+self.printerOffset[0], stagePos[1]+self.printerOffset[1])

    def calibFiducialCamPos(self):
        """Calibrate location of fiducial marker under the camera

        :param stagePos: Stage coordinates for location of fiducial marker
        :type stagePos: tuple
        """
        fiducialCamPos = self.getStageXY()
        self.fiducialCamPos = tuple(fiducialCamPos)
    
    def calibPenPos(self):
        """Calibrate location of pen

        :param stagePos: Stage coordinates for location of pen is centered with the fiducial marker
        :type stagePos: tuple
        """
        penPos = self.getStageXY()
        self.penPos = tuple(penPos)
    
    def moveToOrigin(self):
        """Move to origin
        """
        self.writeRead("G,0,0", isMoveCmd=True)

    def moveChannelToPrinter(self, channelNum: int):
        """Moves specified channel under printer head

        :param channelNum: Channel to move under printer head
        :type channelNum: int
        """

        # Y Position of ith channel under camera
        channelY = self.firstChannelCamPos[1] - \
            ((channelNum - 1) * self.chanStepSize)

        # Add printer offset

        cmd = f"G,{self.firstChannelCamPos[0] + self.printerOffset[0]}, {channelY + self.printerOffset[1]}\r"
        self.writeRead(cmd, isMoveCmd=True)

    def moveWellToPrinter(self, well: str):
        """Move specified well under printer head

        :param well: ID of well. Preferred format = row,column
        :type well: str
        """
        # Convert to row,col if not in that format
        if not "," in well:
            well = self.wellIDToRowCol(well)

        if self.isRealWell(well):
            well = well.split(",")
            row = int(well[0])
            col = int(well[1])

            xOffset = (col-1) * self.wellStepSize * -1
            yOffset = (row-1) * self.wellStepSize * -1

            cmd = f"G,{self.firstWellCamPos[0]+xOffset+self.printerOffset[0]}, \
                {self.firstWellCamPos[1]+yOffset+self.printerOffset[1]}"
            self.writeRead(cmd, isMoveCmd=True)


    def moveChannelToCam(self, chanNum: int):
        """Move specified channel under camera

        :param chanNum: Channel number
        :type chanNum: int
        """
        if self.isRealChannel(chanNum=chanNum):
            yOffset = (chanNum - 1) * self.chanStepSize * -1
            cmd = f"G,{self.firstChannelCamPos[0]},{self.firstChannelCamPos[1]+yOffset}"
            self.writeRead(cmd, isMoveCmd=True)

    def moveDropToCam(self, dropLoc: tuple[int, int]):
        """
        Moves the stage by subtracting offset from the current position.
        Intended to be used to show a drop on the camera.

        :param dropX: x, y location of drop in steps
        :type dropX: tuple[int, int]
        """
        cmd = f"G,{dropLoc[0] - self.printerOffset[0]},{dropLoc[1] - self.printerOffset[1]}"
        self.writeRead(cmd, isMoveCmd=True)

    def camToPrinter(self):
        camPos = self.getStageXY()
        cmd = f"G, {camPos[0] + self.printerOffset[0]},{camPos[1] + self.printerOffset[1]}"
        self.writeRead(cmd, isMoveCmd=True)

    def getStageX(self) -> int:
        """Get X position of the stage (in number of motor steps)

        Take this number and multiply by self.stepSize to get X pos in number of microns from origin

        :return: X position of stage
        :rtype: int
        """
        res = self.writeRead("PX")
        return int(res)

    def getStageY(self) -> int:
        res = self.writeRead("PY")
        return int(res)

    def getStageXY(self):
        res = self.writeRead("P")
        res = res.split(",")
        res = [int(x) for x in res]
        return res[:-1]  # ignore z

    def isMoving(self) -> bool:
        """Check if the stage is moving

        Prior's manual recommends this style of checking for motion

        :return: True if the stage is moving; False otherwise
        :rtype: bool
        """
        start = self.getStageXY()
        end = self.getStageXY()
        return not (start == end)

    # Private helper methods
    # TODO: designate these as private with _

    def isRealWell(self, well: str) -> bool:
        """Check if well with given ID exists on well plate

        :param well: Well ID
        :type well: str
        :return: True if well exists; False otherwise
        :rtype: bool
        """
        # NOTE: the old letter, number system (e.g., A3) is not generalizable
        # For example, 384-well plates exist and are used
        # Better ID system: "row,col"
        well = well.split(",")
        row = int(well[0])
        col = int(well[1])
        plateRows = self.plate.numRows
        plateCols = self.plate.numCols
        if (row < 1 or col < 1 or row > plateRows or col > plateCols):
            print("Row and/or column out of bounds!")
            print(
                f"Currently using {plateRows*plateCols}-well plate with dimensions: {plateRows} rows, {plateCols} columns")
            # raise ValueError("Row and/or column out of bounds!")
            return False
        return True

    def isRealChannel(self, chanNum: int) -> bool:
        """Check if channel with given number exists on chip

        :param chanNum: Channel number
        :type chanNum: int
        :return: True if channel exists; False otherwise
        :rtype: bool
        """
        if(chanNum < 1 or chanNum > self.chip.numChan):
            print("Channel number out of bounds!")
            print(
                f"Currently using chip with {self.chip.numChan} channels"
            )
            return False
        return True

    def wellIDToRowCol(self, wellID: str) -> str:
        """Converts a wellID in the format "A1" to
        a row,col format: 1,1

        :param wellID: String representing ID of the well
        :type wellID: str
        :return: a string in the format (row,col)
        :rtype: str
        """
        row = string.ascii_uppercase.index(wellID[0]) + 1
        col = int(wellID[1:])
        return f"{row},{col}"

    # ======================================== #
    # Raw Stage Movement Commands              #
    # ======================================== #
    def moveXInUM(self, dist: float):
        """Move stage in x-direction by distance

        NOTE: Move stage left => negative distance
        Also since the printer is fixed, moving stage left => moving printer right along devices

        :param dist: Distance (in um) to move stage in x-direction
        :type dist: float
        """
        steps = dist / self.stepSize
        cmd = f"GR,{steps},0"
        self.writeRead(cmd, isMoveCmd=True)

    def moveYInUM(self, dist):
        steps = dist / self.stepSize
        cmd = f"GR,0,{steps}"
        self.writeRead(cmd, isMoveCmd=True)

    def moveToPos(self, x: int, y: int):
        """Move to absolute position

        :param x: Distance (in motor steps) to move stage in x-dir
        :type x: int
        :param y: Distance (in motor steps) to move stage in y-dir
        :type y: int
        """
        cmd = f"G,{x},{y}"
        self.writeRead(cmd, isMoveCmd=True)

    def writeRead(self, cmd: str, isMoveCmd=False) -> str:
        cmd = f"{cmd}\r"
        self.ser.write(cmd.encode())
        # wait until we get back "R" if movement command
        # See PRIOR manual for details if needed
        if isMoveCmd:
            # res = self.ser.readline()
            # while (not (b'R' in res)):
            #     res = self.ser.readline()
            # return res.decode()
            while True:
                if not self.isMoving():
                    return
        else:
            return self.ser.readline().decode()

    def isMoving(self) -> bool:
        """
        Returns true if the stage is moving; otherwise return false
        Used by functions that cause the stage to move so that they can
        successfully block other commands until the movement stops.
        """

        return (self.checkXMoving() or self.checkYMoving()
                or self.checkXMoving() or self.checkYMoving())

    def checkXMoving(self) -> bool:
        """
        Returns whether or not the stage is moving along the x axis
        NOTE: sometimes this goofs
        """
        cmd = "$,X"
        val = self.writeRead(cmd, isMoveCmd=False)
        try:
            return bool(int(val))
        except ValueError as e:
            # print(e)
            pass

    def checkYMoving(self) -> bool:
        """
        Returns whether or not the stage is moving along the y axis
        NOTE: sometimes this goofs
        """
        cmd = "$,Y"
        val = self.writeRead(cmd, isMoveCmd=False)
        try:
            return bool(int(val))
        except ValueError as e:
            # print(e)
            pass

    def close(self):
        """Close serial connection"""
        self.ser.close()

    def loadPrevOffset(self):
        """Loads previously calibrated printer offset values.
        If the data doesn't exist or is unreadable,
        overwrites / creates the file and loads default values
        """
        parentDir = pathlib.Path(__file__).parent.resolve(
        )  # reference to parent directory of this file
        calibPath = os.path.join(parentDir, 'calibrationFiles')
        offsetPath = os.path.join(calibPath, 'offset.txt')

        if not os.path.exists(calibPath):
            # calibration directory doesn't exist
            os.makedirs(calibPath)
            self.__makeDefOffsetFile(pathToData=offsetPath)
        else:
            if not os.path.exists(offsetPath):
                # calibration directory exists, but offset.txt doesn't
                self.__makeDefOffsetFile(pathToData=offsetPath)
            else:
                # calibrationFiles/offset.txt exists
                with open(offsetPath, 'r+') as f:
                    # check if file is well formatted
                    line1 = f.readline()  # can be None
                    line2 = f.readline()  # can be None

                    try:  # this will fail if formatting was bad
                        # if any formatting error, it will happen here
                        offsets = (int(line1), int(line2))
                        self.printerOffset = offsets
                    except:
                        print("file is not formatted correctly, using default values")
                        self.__makeDefOffsetFile(pathToData=offsetPath)

    def restoreDefaultOffset(self):
        """
        Loads and stores the default printer offset values
        Intended to be used when you mess up calibrating and want a clean slate
        """
        parentDir = pathlib.Path(__file__).parent.resolve()
        calibPath = os.path.join(parentDir, 'calibrationFiles')
        offsetPath = os.path.join(calibPath, 'offset.txt')
        self.__makeDefOffsetFile(pathToData=offsetPath)

    def saveNewOffset(self, newX: int, newY: int):
        """
        Saves a new (x,y) offset in the device and writes them
        to a file for future use

        :param newX: new x offset ( in steps )
        :type newX: int
        :param newY: new y offset ( in steps )
        :type newY: int
        """
        parentDir = pathlib.Path(__file__).parent.resolve()
        calibPath = os.path.join(parentDir, 'calibrationFiles')
        offsetPath = os.path.join(calibPath, 'offset.txt')

        if not os.path.exists(calibPath):
            os.makedirs(calibPath)

        with open(offsetPath, 'w+') as f:
            self.printerOffset = (newX, newY)
            f.write(f"{str(newX)}\n")
            f.write(str(newY))

    def __makeDefOffsetFile(self, pathToData, defaultX: int = -50000, defaultY: int = -50000):
        """
        Helper function to load default printer offset values
        and store them in a file

        TODO: get more accurate default offset values

        :param pathToData: path to the file in which offset values are stored
        :type pathToData: str
        :param defaultX: default X offset, defaults to -50000
        :type defaultX: int, optional
        :param defaultY: default Y offset, defaults to -50000
        :type defaultY: int, optional
        """
        self.printerOffset = (defaultX, defaultY)

        with open(pathToData, 'w+') as f:
            f.write(f"{str(defaultX)}\n")
            f.write(str(defaultY))

    def loadPrevFirstChan(self):
        """
        Loads most recently saved first channel (x,y) values.
        If the data doesn't exist or is unreadable, this method
        will overwrite / create the file and load the default values
        """
        parentDir = pathlib.Path(__file__).parent.resolve()
        calibPath = os.path.join(parentDir, 'calibrationFiles')
        channelPath = os.path.join(calibPath, 'firstChannel.txt')

        if not os.path.exists(calibPath):
            # calibration folder doesn't exist
            os.makedirs(calibPath)
            self.__makeDefFirstChannelFile(pathToData=channelPath)
        else:
            if not os.path.exists(channelPath):
                # calibration folder exists, but file holding channel values doesn't
                self.__makeDefFirstChannelFile(pathToData=channelPath)
            else:
                # the first channel calibration file and exists
                with open(channelPath, 'r+') as f:
                    line1 = f.readline() # can be None
                    line2 = f.readline()  # can be None

                    try:  # this will fail if formatting was bad
                        # if any formatting error, it will happen here
                        chanLoc = (int(line1), int(line2)) # error would happen here, before setting
                        self.firstChannelCamPos = chanLoc
                    except:
                        print("file is not formatted correctly, using default values")
                        self.__makeDefFirstChannelFile(pathToData=channelPath)

    def restoreDefaultFirstChannel(self):
        """
        Resets the stored first channel location, storing the
        default values in the calibration file and loading the
        default values into the stage
        """
        parentDir = pathlib.Path(__file__).parent.resolve()
        calibPath = os.path.join(parentDir, 'calibrationFiles')
        channelPath = os.path.join(calibPath, 'firstChannel.txt')
        self.__makeDefFirstChannelFile(pathToData=channelPath)

    def saveNewFirstChannel(self, stagePos: tuple[int, int]):
        # TODO: this should replace setFirstChannel
        """
        Grabs the position of the stage and stores it as the
        'first channel on camera' position. Also stores those
        values in a file to be used on future experiments
        """
        parentDir = pathlib.Path(__file__).parent.resolve()
        calibPath = os.path.join(parentDir, 'calibrationFiles')
        channelPath = os.path.join(calibPath, 'firstChannel.txt')

        if not os.path.exists(calibPath):
            os.makedirs(calibPath)

        with open(channelPath, 'w+') as f:
            # x = self.getStageX()
            # y = self.getStageY()
            x = stagePos[0]
            y = stagePos[1]

        # already saved by calibFirstChannelCamPos
            # self.firstChannelCamPos = tuple((x, y))

            f.write(f"{str(x)}\n")
            f.write(str(y))

    # NOTE: can change these defaults in the future
    def __makeDefFirstChannelFile(self, pathToData: str, defaultX: int = -2016268, defaultY: int = -1409635):
        """
        Helper method to create / overwrite the stored first channel location with default values.
        Also loads those default values into the stage

        :param pathToData: path to file holding first channel values
        :type pathToData: str
        :param defaultX: default x value (in steps), defaults to -1635268
        :type defaultX: int, optional
        :param defaultY: default y value (in steps), defaults to -1537768
        :type defaultY: int, optional
        """
        self.firstChannelCamPos = (defaultX, defaultY)

        with open(pathToData, 'w+') as f:
            f.write(f"{str(defaultX)}\n")
            f.write(str(defaultY))

    # first well stuff
    def loadPrevFirstWellPos(self):
        """
        Loads most recently saved first well (x,y) values.
        If the data doesn't exist or is unreadable, this method
        will overwrite / create the file and load the default values
        """
        parentDir = pathlib.Path(__file__).parent.resolve()
        calibPath = os.path.join(parentDir, 'calibrationFiles')
        wellPath = os.path.join(calibPath, 'firstWell.txt')

        if not os.path.exists(calibPath):
            # calibration folder doesn't exist
            os.makedirs(calibPath)
            self.__makeDefFirstWellPosFile(pathToData=wellPath)
        else:
            if not os.path.exists(wellPath):
                # calibration folder exists, but file holding channel values doesn't
                self.__makeDefFirstWellPosFile(pathToData=wellPath)
            else:
                # the first channel calibration file and exists
                with open(wellPath, 'r+') as f:
                    line1 = f.readline() # can be None
                    line2 = f.readline()  # can be None

                    try:  # this will fail if formatting was bad
                        # if any formatting error, it will happen here
                        wellLoc = (int(line1), int(line2)) # error would happen here, before setting
                        self.firstWellCamPos = wellLoc
                    except:
                        print("file is not formatted correctly, using default values")
                        self.__makeDefFirstWellPosFile(pathToData=wellPath)

    def restoreDefaultFirstWellPos(self):
        """
        Resets the stored first well location, storing the
        default values in the calibration file and loading the
        default values into the stage
        """
        parentDir = pathlib.Path(__file__).parent.resolve()
        calibPath = os.path.join(parentDir, 'calibrationFiles')
        wellPath = os.path.join(calibPath, 'firstWell.txt')
        self.__makeDefFirstWellPosFile(pathToData=wellPath)

    def saveNewFirstWellPos(self, stagePos: tuple[int, int]):
        # TODO: this should replace calibFirstWell
        """
        Grabs the position of the stage and stores it as the
        'first well centered on camera' position. Also stores those
        values in a file to be used on future experiments
        """
        parentDir = pathlib.Path(__file__).parent.resolve()
        calibPath = os.path.join(parentDir, 'calibrationFiles')
        channelPath = os.path.join(calibPath, 'firstWell.txt')

        if not os.path.exists(calibPath):
            os.makedirs(calibPath)

        with open(channelPath, 'w+') as f:
            x = stagePos[0]
            y = stagePos[1]

            # self.firstChannelCamPos = tuple((x, y))

            f.write(f"{str(x)}\n")
            f.write(str(y))

    # NOTE: can change these defaults in the future
    def __makeDefFirstWellPosFile(self, pathToData: str, defaultX: int = -2467571, defaultY: int = 520509):
        """
        Helper method to create / overwrite the stored first well location with default values.
        Also loads those default values into the stage

        :param pathToData: path to file holding first well values
        :type pathToData: str
        :param defaultX: default x value (in steps), defaults to -1635268
        :type defaultX: int, optional
        :param defaultY: default y value (in steps), defaults to -1537768
        :type defaultY: int, optional
        """
        self.firstWellCamPos = (defaultX, defaultY)

        with open(pathToData, 'w+') as f:
            f.write(f"{str(defaultX)}\n")
            f.write(str(defaultY))