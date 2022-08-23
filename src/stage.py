import serial
from plate import *
from chip import *
import time

# The "Stage" really encompasses the whole setup on top of the stage- Chip, Plate, and microscope stage


class Stage:
    # TODO: change the default values for firstWellPos, they are bogus
    def __init__(self, plate: Plate, chip: Chip, port="COM6", baudrate=9600, timeout=0.1, stepSize=0.04):
        self.ser = serial.Serial(port, baudrate, timeout=timeout)
        self.plate = plate
        self.chip = chip

        self.stepSize = stepSize
        # BUG: possible bug here, stepChanSize is defined as number of stage motor steps between centers of 2 adjacent wells
        # self.chanStepSize = self.chip.chanGapWidth / self.stepSize
        self.wellStepSize = self.plate.diam / self.stepSize

        # TODO: used to have self.plateInitX, plateInitY
        # We should standardize that initial reference well is A1, since there is no guarantee which well plate is being used
        

    def setOrigin(self):
        # TODO: make a note of this in the official docs
        # Since (0, 0) is bottom right, stage up => y decreases, stage left => x decreases

        self.writeRead("G,0,0", isMoveCmd=True) # Move stage to absolute 0,0 position
        self.writeRead("P,0,0,0") # Define this location as origin
        # Prior advises that SIS only be used upon first installation

    
    # Set coordinates for well A1 on stage
    # Again, we justify that the "stage" encapsulates the actual microscope stage + well/chip on top of it
    def setFirstWellPos(self):
        # Assume user has positioned printer head above center of well A1
        stagePos = self.getStageXY()
        self.firstWellPos = tuple(stagePos)


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
        return res[:-1] # ignore z

    # Prior's manual recommends this style of checking for motion
    def isMoving(self) -> bool:
        start = self.getStageXY()
        end = self.getStageXY()
        return not(start == end)        


        
    # Expecting no response
    # def write(self, cmd: str):
    #     cmd = f"{cmd}\r"
    #     self.ser.write(cmd.encode())


    # Expecting response
    def writeRead(self, cmd: str, isMoveCmd=False) -> str:
        cmd = f"{cmd}\r"
        self.ser.write(cmd.encode())
        # wait until we get back "R" if movement command
        if isMoveCmd:
            res = self.ser.readline()
            while(not(b'R' in res)):
                res = self.ser.readline()
            return res.decode()
        else:
            return self.ser.readline().decode()
    

    def close(self):
        self.ser.close()

    
