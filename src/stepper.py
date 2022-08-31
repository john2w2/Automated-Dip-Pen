import serial
import time

class Screw:

    def __init__(self, numStarts=2, tpi=13):
        self.numStarts = numStarts
        self.tpi = tpi

    def getLead(self) -> float:
        """Get lead value, i.e. how far an object attached to the screw moves per one revolution of screw

        :return: lead value for screw
        :rtype: float
        """
        # Lead = distance a nut moves per one revolution of the screw
        # TPI = Threads Per Inch. Count number of thread peaks per inch
        # Pitch = distance between crest threads = 1/ TPI
        # NOTE: better to calculate TPI, measuring pitch yourself could lead to inaccuracy
        # Number of starts = number of ridges wrapped around screw body (go see a picture)
        # NOTE: standard screw has 1 start, though ours has 2

        # Lead = pitch * number of starts
        pitch = 1 / self.tpi  # in inches
        pitch = pitch * 25.4  # convert inches to mm
        lead = pitch * self.numStarts
        return lead


class Stepper:

    """This class represents a Stepper motor

    """

    def __init__(self, screw: Screw, stepsPerRev=200):
        self.screw = screw
        self.stepsPerRev = stepsPerRev
        # note: stepper motor is called {stepsPerRev}-step motor (e.g., 200-step motor)

        # Vertical distance attached object will move (in um) per step of motor
        self.distPerStep = self.screw.getLead() / self.stepsPerRev * 1000


class ZMotor:
    def __init__(self, stepper: Stepper, port="COM7", baudrate=115200, timeout=0.1):
        self.stepper = stepper
        self.arduino = serial.Serial(
            port=port, baudrate=baudrate, timeout=timeout)

        # TODO: you have to wait?
        time.sleep(2)

    def calibrateOrigin(self):
        """Move arm until it hits topmost limit switch, saves that position as origin
        """

        self.__sendCommand("calibrateOrigin")
        self.__waitForIdle()

    def interrupt(self):
        """Stop all movement
        """
        self.__sendCommand("INTERRUPT")

    def moveToZInSteps(self, steps: int):
        """Move arm to specified absolute Z position (in number of motor steps)

        Origin is set at topmost position, so to move down, pass in negative value

        :param steps: distance (in number of motor steps) from the top
        :type steps: int
        """

        cmd = f"moveToZAbsolute {steps}"
        self.__sendCommand(cmd)
        self.__waitForIdle()

    def moveToZInUM(self, dist):
        """Move arm to specified absolujte Z position (in um)

        Example:
        ```
        zm.moveToZInMM(-3000)
        ```

        :param dist: distance (in um) from the top
        :type dist: int
        """

        numSteps = int(dist / self.stepper.distPerStep)
        self.moveToZInSteps(numSteps)

    def moveToZRelInUM(self, dist:int):
        """Move arm by amount=dist, relative to current position

        :param dist: Amount to move by (in um)
        :type dist: int
        """
        # dist in um
        pos = self.getZPosInUM()
        newPos = pos + dist
        self.moveToZInUM(newPos)


    def moveToZRelInMM(self, dist:int):
        """Move arm by amount=dist, relative to current position

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

