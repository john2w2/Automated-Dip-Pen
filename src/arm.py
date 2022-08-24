import serial
from stepper import Stepper
import time

class ZMotor:
    def __init__(self, stepper: Stepper, port="COM7", baudrate=115200, timeout=0.1):
        self.stepper = stepper
        self.arduino = serial.Serial(
            port=port, baudrate=baudrate, timeout=timeout)

        # TODO: you have to wait?
        time.sleep(2)


    def calibrateOrigin(self):
        """
        Move arm until it hits topmost limit switch,
        saves that position as 0
        """

        self.__sendCommand("calibrateOrigin")
        self.__waitForIdle()

    def interrupt(self):
        """
        Issues an INTERRUPT command, stopping any movement
        NOTE: interrupt does not emit an additional idle signal,
            but the idle signal tied to the original movement command
            will still be emitted
        """
        self.__sendCommand("INTERRUPT")


    def moveToZAbsoluteSteps(self, steps: int):
        """
        Move arm to the specified Z position (in number of motor steps)
        """

        cmd = f"moveToZAbsolute {steps}"
        self.__sendCommand(cmd)
        self.__waitForIdle()   

    
    def getZSteps(self) -> int:
        """
        Get (in number of motor steps) distance of arm from the top-most position
        """

        self.__sendCommand("getZPosition")
        res = self.__readSerial()
        return(int(res))


   
    def close(self):
        """
        Close the serial connection to the arduino.
        Must be called when program is shuttting down
        """
        self.arduino.close()

    # =============================================== #
    # Private helper methods                          #
    # =============================================== #

    def __sendCommand(self, cmd: str):
        cmd = f"{cmd}\r"    # carriage return indicates end of command
        self.arduino.write(cmd.encode())

    def __waitForIdle(self):
        """
        Waits for the arduino to finish any movement command before
        returning. Used so multiple movement commands don't execute
        at the same time.
        Consumes all buffered serial lines until it sees 'idle'
        """ 
        while True:
            if self.arduino.in_waiting:
                if "idle" in self.arduino.readline().decode(): # for some reason response == "idle" doesn't work
                    # just be careful not to emit any other signal containing idle
                    return

    def __readSerial(self) -> str: 
        """
        Read a line from serial and return it
        """
        while True:
            if self.arduino.in_waiting:
                return self.arduino.readline().decode()


class Arm:
    def __init__(self, zmotor:ZMotor):
        self.zmotor = zmotor

    def calibrateOrigin(self):
        self.zmotor.calibrateOrigin()

    # def moveToOrigin(self, )

    def stopArm(self):
        self.zmotor.interrupt()

    # TODO: finish this class
    

