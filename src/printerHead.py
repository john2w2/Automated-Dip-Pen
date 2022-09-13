import serial
from voltage import Voltage
from pressure import Pressure

class PrinterHead:
    # TODO: is this class even necessary ? it just calls single methods
    # but, it semantically combines the devices into one quite nicely
    # I just can't get over how these functions just call another function
    def __init__(self, priorController:serial.Serial):
        self.pressure = Pressure()
        self.voltage = Voltage(priorController)
        # TODO: store current sample here?

    def printSingle(self):
        self.voltage.print()

    def getSample(self):
        self.pressure.inThenHold()

    def dispenseSample(self):
        self.pressure.blowOut()    

    def calibPressureSystem(self):
        self.pressure.calibrate()

    def savePressures(self, inP, eqP, outP):
        self.pressure.savePressureVals(inP, eqP, outP)

    def stopPressure(self):
        self.pressure.stop()

    def close(self):
        self.pressure.close()
        self.voltage.close()
