from stepper import ZMotor

class Arm:
    # TODO: later, pass in YMotor
    def __init__(self, zmotor: ZMotor):
        self.zmotor = zmotor

    def calibrateOrigin(self):
        self.zmotor.calibrateOrigin()
        # TODO: self.ymotor.calibrateOrigin() later on

    # TODO: also automate setting positions for printing, acquiring sample, etc.
    # or is "eyeballing" this safe enough?
    # In the case that automation is necessary, have to take some precise measurements - heights, etc.


    def stopArm(self):
        """Immediately stop all movement on the arm

        Intended to be called from a thread secondary to the one controlling
        the arm, since that main thread will be blocked
        """
        self.zmotor.interrupt()

    # TODO: finish this class
