import serial
import time

class Voltage:
    def __init__(self, priorController: serial.Serial):
        self.ser = priorController
        self.shockDuration = 0.2
        self.waitTime = 5.0 

    def print(self):
        time.sleep(self.waitTime)
        self.writeCmd("TTL,0,1")
        time.sleep(self.shockDuration)
        self.writeCmd("TTL,0,0")
        time.sleep(0.1)
        self.clearSer()
        time.sleep(self.waitTime)

    def setWait(self, wait: float):
        """Sets the before and after wait time for printing

        :param wait: time in seconds 
        :type wait: float
        """
        self.waitTime = wait

    def writeCmd(self, cmd):
        cmd = f"{cmd}\r"
        self.ser.write(cmd.encode())

    def clearSer(self):
        self.ser.read_all()

    # NOTE: on program shutdown, we should send a TTL,0,0
    # to make sure no voltage is being applied
    # TODO: maybe this should be moved somewhere else
    def close(self):
        self.writeCmd("TTL,0,0")