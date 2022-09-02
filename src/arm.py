from stepper import ZMotor

class Arm:
    # TODO: later, pass in YMotor
    def __init__(self, zmotor: ZMotor):
        self.zmotor = zmotor

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

    def stopArm(self):
        self.zmotor.interrupt()
