import serial

from stepper import ZMotor
from time import sleep # for waiting for priorController to start up

class Arm:
    # TODO: later, pass in YMotor
    def __init__(self, arduinoPort): # TODO: pass in arduinoController here
        # since serial connection made here, we will wait for it to be ready here as well
        self.arduinoController = serial.Serial(port=arduinoPort, baudrate=115200, timeout=0.1)
        self.waitForReady(self.arduinoController)

        self.zmotor = ZMotor(arduinoController=self.arduinoController)

        # NOTE: these are all placeholder
        # TODO: load positions from file
        self.zUpPos = -100 
        self.zWellPos = -200
        self.zChannelPos = -150

    def calibrateOrigin(self):
        self.zmotor.calibrateOrigin()
        # TODO: self.ymotor.calibrateOrigin() later on

    def moveToOrigin(self):
        self.zmotor.moveToZInSteps(0)

    # TODO: also automate setting positions for printing, acquiring sample, etc.
    # or is "eyeballing" this safe enough?
    # In the case that automation is necessary, have to take some precise measurements - heights, etc.
    # 3 positions to be calibrated: "up", "into well for pickup", "above channel for printing"
    def calibZUpPos(self):
        pos = self.zmotor.getZPosInSteps()
        self.zUpPos = pos

    def calibZWellPos(self):
        pos = self.zmotor.getZPosInSteps()
        self.zWellPos = pos

    def calibZChannelPos(self):
        pos = self.zmotor.getZPosInSteps()
        self.zChannelPos = pos

    def moveZUpPos(self):
        # TODO: add check that self.zUpPos exists
        self.zmotor.moveToZInSteps(self.zUpPos)

    def moveZWellPos(self):
        self.zmotor.moveToZInSteps(self.zWellPos)

    def moveZChannelPos(self):
        self.zmotor.moveToZInSteps(self.zChannelPos)

    def interruptArm(self):
        self.zmotor.interrupt()

    def close(self):
        self.arduinoController.close()

    def waitForReady(self, arduinoController: serial.Serial):
        while not arduinoController.in_waiting:
            sleep(0.01)
        arduinoController.readline() # consumes first line, which should be 'arduino ready\r\n'