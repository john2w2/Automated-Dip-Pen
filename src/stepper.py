import serial

class Screw:
    """
    This class represents the screw attached to a stepper motor

    :param numStarts: Number of ridges wrapped around screw body
    :type numStarts: int, optional
    :param tpi: Threads Per Inch. Count number of thread peaks per inch
    :type tpi: int, optional
    """

    def __init__(self, numStarts=4, tpi=12.7):
        """Constructor
        """
        self.numStarts = numStarts
        self.tpi = tpi

    def getLead(self) -> float:
        """Get lead value, i.e. how far an object attached to the screw moves per one revolution of screw

        :return: lead value for screw
        :rtype: float
        """
        # Lead = distance a nut moves per one revolution of the screw, pitch * number of starts
        # TPI = Threads Per Inch. Count number of thread peaks per inch. 9/9/2025 update: T8x8 lead screw has a 2 mm pitch, which is 12.7 TPI
        # Pitch = distance between crest threads = 1/ TPI
        # NOTE: better to calculate TPI, measuring pitch yourself could lead to inaccuracy
        # Number of starts = number of ridges wrapped around screw body (go see a picture)
        # NOTE: standard screw has 1 start, though ours has 4

        # Lead = pitch * number of starts
        pitch = 1 / self.tpi  # in inches
        pitch = pitch * 25.4  # convert inches to mm
        lead = pitch * self.numStarts
        return lead

# TODO: merge
class Stepper:

    """
    This class represents a Stepper motor

    :param screw: Screw attached to stepper motor
    :type screw: class:`stepper.Screw`
    :param stepsPerRev: Number of motor steps for a full revolution (360 degrees)
    :type stepsPerRev: int, optional
    """

    def __init__(self, screw: Screw, stepsPerRev=400):
        self.screw = screw
        self.stepsPerRev = stepsPerRev
        # note: stepper motor is called {stepsPerRev}-step motor (e.g., 200-step motor) 

        # 7/14/2025 update:
        # Main goal is to migrate the current configuration to dipping and place system, i.e. 
        # getting rid of voltage and flow components. I upgraded the system to have 0.9 deg 
        # stepper motor (400 stepsPerRev).

        # Vertical distance attached object will move (in um) per step of motor
        self.distPerStep = self.screw.getLead() / self.stepsPerRev * 1000


class ZMotor:
    """
    This class represents the Z-Axis Motor responsible for moving Arm up/down

    :param stepper: Stepper motor for Z-Axis Motor
    :type stepper: class:`stepper.Stepper`
    :param port: Name of serial port
    :type port: str, optional
    :param baudrate: Max rate at which information transferred, (in bits/s)
    :type baudrate: int, optional
    :param timeout: Timeout for serial read() (in seconds)
    :type timeout: float, optional

    """
    # TODO: add constructor parameters: numStarts, TPI
    def __init__(self, arduinoController: serial.Serial, numStarts=4, tpi=12.7, stepsPerRev=400):
        self.screw = Screw(numStarts=numStarts, tpi=tpi)
        self.stepper = Stepper(screw=self.screw, stepsPerRev=stepsPerRev)
        self.arduino = arduinoController

    def calibrateOrigin(self):
        """Move arm until it triggers the optical endstop, saves that position as origin
        """

        self.__sendCommand("calibrateOrigin")
        self.__waitForIdle()

    def interrupt(self):
        """Stop all movement. Also will stop y motor
        """
        self.__sendCommand("INTERRUPT")

    def moveToZInSteps(self, steps: int):
        """Move arm to specified absolute Z position (in number of motor steps)

        Origin is set at topmost position, so to move down, pass in negative value

        :param steps: Distance (in number of motor steps) from the top
        :type steps: int
        """

        cmd = f"moveToZAbsolute {steps}"
        self.__sendCommand(cmd)
        self.__waitForIdle()

    def moveToZInUM(self, dist):
        """Move arm to specified absolute Z position (in um)

        Example:
        ```
        zm.moveToZInUM(-3000)
        ```

        :param dist: Distance (in um) from the top
        :type dist: int
        """

        numSteps = int(dist / self.stepper.distPerStep)
        self.moveToZInSteps(numSteps)

    def moveToZRelInUM(self, dist:int):
        """Move arm by specified distance, relative to current position

        :param dist: Amount to move by (in um)
        :type dist: int
        """
        # dist in um
        pos = self.getZPosInUM()
        newPos = pos + dist
        self.moveToZInUM(newPos)


    def moveToZRelInMM(self, dist:int):
        """Move arm by specified distance, relative to current position

        :param dist: Amount to move by (in mm)
        :type dist: int
        """
        self.moveToZRelInUM(dist * 1000)


    def getZPosInSteps(self) -> int:
        """Get (in number of motor steps) distance of arm from topmost position

        :return: Vertical distance of arm (in motor steps) from topmost position
        :rtype: int
        """

        self.__sendCommand("getZPosition")
        res = self.__readSerial()
        return (int(res))

    def getZPosInUM(self) -> float:
        """Get (in um) distance of arm from topmost position

        :return: Vertical distance of arm (in um) from topmost position
        :rtype: float
        """
        pos = self.getZPosInSteps()
        return pos * self.stepper.distPerStep

    def close(self):
        # TODO: I don't think we need this since we call arduinoController.close() in arm.py/Arm
        """Close serial connection to Arduino

        Must be called when program is shuttting down
        """
        self.arduino.close()

    # =============================================== #
    # Private helper methods                          #
    # =============================================== #

    def __sendCommand(self, cmd: str):
        cmd = f"{cmd}\r"
        self.arduino.write(cmd.encode())

    def __waitForIdle(self):
        while True:
            if self.arduino.in_waiting:
                if "idle" in self.arduino.readline().decode():
                    return

    def __readSerial(self) -> str:
        while True:
            if self.arduino.in_waiting:
                return self.arduino.readline().decode()

class YMotor:
    def __init__(self, arduinoController):
        self.arduino = arduinoController

    def moveYRelInSteps(self, steps):
        cmd = f"moveByY {steps}"
        self.__sendCommand(cmd)
        self.__waitForIdle()

    def __sendCommand(self, cmd: str):
        cmd = f"{cmd}\r"
        self.arduino.write(cmd.encode())

    def __waitForIdle(self):
        while True:
            if self.arduino.in_waiting:
                if "idle" in self.arduino.readline().decode():
                    return