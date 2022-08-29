import serial
from plate import *
from chip import *
import time

# The "Stage" really encompasses the whole setup on top of the stage- Chip, Plate, and microscope stage


class Stage:

    # stepSize = distance (im um) a single motor step will move the stage
    def __init__(self, plate: Plate, chip: Chip, port="COM6", baudrate=9600, timeout=0.1, stepSize=0.04):
        self.ser = serial.Serial(port, baudrate, timeout=timeout)
        self.plate = plate
        self.chip = chip

        # TODO: for convenience right now, change later  - let files be loaded in
        self.firstWellPos = (-2147477, -293671)
        self.firstChannelCamPos = (-2016268, -1409635)

        self.stepSize = stepSize

        # This is the distance (in motor steps) between centers of 2 adjacent channels
        self.chanStepSize = (self.chip.chanGapWidth+self.chip.chanWidth) / self.stepSize
        self.wellStepSize = self.plate.diam / self.stepSize

        # TODO: used to have self.plateInitX, plateInitY
        # We should standardize that initial reference well is A1, since there is no guarantee which well plate is being used

    def setOrigin(self):
        # TODO: make a note of this in the official docs
        # Since (0, 0) is bottom right, stage up => y decreases, stage left => x decreases

        # Move stage to absolute 0,0 position
        self.writeRead("G,0,0", isMoveCmd=True)
        self.writeRead("P,0,0,0")  # Define this location as origin
        # Prior advises that SIS only be used upon first installation, possibly avoid

    # Set coordinates for well A1 on stage
    # Again, we justify that the "stage" encapsulates the actual microscope stage + well/chip on top of it
    def setFirstWellPos(self) -> tuple:
        # Assume user has positioned printer head above center of well A1
        # TODO: remove this assumption later, have this be automated for accuracy
        stagePos = self.getStageXY()
        self.firstWellPos = tuple(stagePos)

    def moveToWell(self, well: str):
        if self.isRealWell(well):
            well = well.split(",")
            row = int(well[0])
            col = int(well[1])
            
            xOffset = (col-1) * self.wellStepSize * -1
            yOffset = (row-1) * self.wellStepSize * -1

            cmd = f"G,{self.firstWellPos[0]+xOffset},{self.firstWellPos[1]+yOffset}"
            self.writeRead(cmd, isMoveCmd=True)


    def setFirstChannelCamPos(self) -> tuple:
        stagePos = self.getStageXY()
        self.firstChannelCamPos = tuple(stagePos)

    def moveToChannelCam(self, chanNum: int):
        if self.isRealChannel(chanNum=chanNum):
            yOffset = (chanNum - 1) * self.chanStepSize * -1
            cmd = f"G,{self.firstChannelCamPos[0]},{self.firstChannelCamPos[1]+yOffset}"
            self.writeRead(cmd, isMoveCmd=True)
      

    def getStageX(self) -> int:
        """Gets the X position of the stage (in number of motor steps)

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

    # Prior's manual recommends this style of checking for motion
    def isMoving(self) -> bool:
        start = self.getStageXY()
        end = self.getStageXY()
        return not (start == end)

    # Private helper methods
    # TODO: designate these as private with _

    def isRealWell(self, well: str) -> bool:
        """Return if well with given ID exists on well plate

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
        if(chanNum < 1 or chanNum > self.chip.numChan):
            print("Channel number out of bounds!")
            print(
                f"Currently using chip with {self.chip.numChan} channels"
            )
            return False
        return True


    ### Pure stage movement commands
    # distance in microns
    def moveXInUM(self, dist):
        steps = dist / self.stepSize
        

    # Expecting response
    def writeRead(self, cmd: str, isMoveCmd=False) -> str:
        cmd = f"{cmd}\r"
        self.ser.write(cmd.encode())
        # wait until we get back "R" if movement command
        if isMoveCmd:
            res = self.ser.readline()
            while (not (b'R' in res)):
                res = self.ser.readline()
            return res.decode()
        else:
            return self.ser.readline().decode()

    def close(self):
        self.ser.close()
