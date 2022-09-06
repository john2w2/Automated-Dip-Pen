import serial
from plate import *
from chip import *
import time

class Stage:
    """
    This class represents the microscope stage and attached devices (well plate and chip)

    Many methods in this class enable required stage movements for the rest of the system, such as
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

    def __init__(self, plate: Plate, chip: Chip, priorController : serial.Serial, stepSize=0.04):
        """Constructor
        """

        self.ser = priorController
        self.plate = plate
        self.chip = chip

        # TODO: for convenience right now, change later  - let files be loaded in
        self.firstWellPos = (-2147477, -293671)
        self.firstChannelCamPos = (-2016268, -1409635)

        self.stepSize = stepSize

        # Derived Fields:
        # Distance (in motor steps) between centers of 2 adjacent channels
        self.chanStepSize = (self.chip.chanGapWidth+self.chip.chanWidth) / self.stepSize
        # Distance (in motor steps) between centers of 2 adjacent wells
        self.wellStepSize = self.plate.diam / self.stepSize

        # NOTE: we used to have self.plateInitX, plateInitY
        # We should standardize that initial reference well is A1, since there is no guarantee which well plate is being used
        # At least we know for any well plate, A1 exists

    
    def calibPrinterOffset(self, offsetX: int, offsetY: int):
        """
        Saves the offset of the printer head
        Offset values come from GUI calibration method

        :param offsetX: distance (in steps) stage has to move to put first 
            channel under printer head, starting from first channel
            being focused on cross of camera (along x axis)
            offsetX = printerDropX - focusedDropX
        :type offsetX: int
        :param offsetY: distance (in steps) stage has to move to put first 
            channel under printer head, starting from first channel
            being focused on cross of camera (along x axis)
            offsetY = printerDropY - focusedDropY
        :type offsetY: int
        """
        self.offset = (offsetX, offsetY)

    def moveChannelToPrinter(self, channelNum: int):
        pass
        # TODO: implement

    def calibOrigin(self):
        """User moves the stage then that position is set as origin
        """
        # NOTE: Since (0, 0) is bottom right, stage up => y decreases, stage left => x decreases

        # self.writeRead("G,0,0", isMoveCmd=True) # Move to origin
        # NOTE: now, have user use joystick to move stage to real origin
        self.writeRead("P,0,0,0")  # Redefine this location as origin
        # NOTE: Prior advises that SIS only be used upon first installation, possibly avoid
        # TODO: bring back SIS possibly

    def moveToOrigin(self):
        self.writeRead("G,0,0", isMoveCmd=True) # Move to origin

    # Set coordinates for well A1 on stage
    # Again, we justify that the "stage" encapsulates the actual microscope stage + well/chip on top of it
    def setFirstWellPos(self) -> tuple:
        # Assume user has positioned printer head above center of well A1
        # TODO: remove this assumption later, have this be automated for accuracy
        stagePos = self.getStageXY()
        self.firstWellPos = tuple(stagePos)

    def moveToWell(self, well: str):
        """Move specified well under printer head

        :param well: ID of well. Format = row,column
        :type well: str
        """
        if self.isRealWell(well):
            well = well.split(",")
            row = int(well[0])
            col = int(well[1])

            xOffset = (col-1) * self.wellStepSize * -1
            yOffset = (row-1) * self.wellStepSize * -1

            cmd = f"G,{self.firstWellPos[0]+xOffset},{self.firstWellPos[1]+yOffset}"
            self.writeRead(cmd, isMoveCmd=True)


    def setFirstChannelCamPos(self) -> tuple:
        """Calibrate location of first channel under the camera

        TODO: this is a calibration function, possibly move
        """
        stagePos = self.getStageXY()
        self.firstChannelCamPos = tuple(stagePos)

    def moveChannelToCam(self, chanNum: int):
        """Move specified channel under camera

        :param chanNum: Channel number
        :type chanNum: int
        """
        if self.isRealChannel(chanNum=chanNum):
            yOffset = (chanNum - 1) * self.chanStepSize * -1
            cmd = f"G,{self.firstChannelCamPos[0]},{self.firstChannelCamPos[1]+yOffset}"
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

    #### Private helper methods
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


    def isRealChannel(self, chanNum:int) -> bool:
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


    def moveToPos(self, x:int, y:int):
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
            res = self.ser.readline()
            while (not (b'R' in res)):
                res = self.ser.readline()
            return res.decode()
        else:
            return self.ser.readline().decode()

    def close(self):
        """Close serial connection
        """
        self.ser.close()
