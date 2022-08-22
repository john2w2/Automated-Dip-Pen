import serial
from plate import *
from chip import *

# The "Stage" really encompasses the whole setup on top of the stage- Chip, Plate, and microscope stage


class Stage:
    def __init__(self, plate: Plate, chip: Chip, port="COM6", baudrate=9600, stepSize=0.04):
        self.ser = serial.Serial(port, baudrate, timeout=0.1)
        self.plate = plate
        self.chip = chip

        self.stepSize = stepSize
        # BUG: possible bug here, stepChanSize is defined as number of stage motor steps between centers of 2 adjacent wells
        # self.chanStepSize = self.chip.chanGapWidth / self.stepSize
        self.wellStepSize = self.plate.diam / self.stepSize

        # TODO: used to have self.plateInitX, plateInitY
        # We should standardize that initial reference well is A1, since there is no guarantee which well plate is being used

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

        
    # Expecting no response
    def write(self, cmd: str):
        cmd = f"{cmd}\r"
        self.ser.write(cmd.encode())


    # Expecting response
    def writeRead(self, cmd: str) -> str:
        cmd = f"{cmd}\r"
        self.ser.write(cmd.encode())
        res = self.ser.readline().decode()
        return res
    

    def close(self):
        self.ser.close()

    
