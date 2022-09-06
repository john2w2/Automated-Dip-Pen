import serial
import time

class Voltage:
    def __init__(self, port="COM8"):
        self.ser = serial.Serial(port=port, baudrate=9600, timeout=0.1)

    def print(self):
        self.writeCmd("TTL,0,1")
        time.sleep(0.2)
        self.writeCmd("TTL,0,0")

    def writeCmd(self, cmd):
        cmd = f"{cmd}\r"
        self.ser.write(cmd.encode())