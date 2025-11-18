# import serial
# from voltage import Voltage
# from pressure import Pressure

# class PrinterHead:
#     def __init__(self, priorController:serial.Serial):
#         self.pressure = Pressure()
#         self.voltage = Voltage(priorController)
#         # TODO: store current sample here?

#     def printSingleDrop(self):
#         """
#         Toggles the JetDrive box, applying a voltage
#         to the printer head with the parameters specified
#         by JetServer
#         """
#         self.voltage.print()

#     def getSample(self):
#         """
#         Applies the in pressure to the printer head for 1 second
#         """
#         self.pressure.inThenHold()

#     def dispenseSample(self):
#         """
#         Applies the out pressure to the printer head for 2 seconds
#         """
#         self.pressure.dispense()

#     def calibPressureSystem(self):
#         """
#         Runs the OB1 automatic calibration process, which takes about 3 minutes.
#         Make sure the OB1 has all channels capped, or something will go terribly wrong.
#         """
#         self.pressure.calibrate()

#     def calibPressureVals(self, inP, eqP, outP):
#         self.pressure.calibPressureValues(inP, eqP, outP)

#     def stopPressure(self):
#         """
#         Immediately sets the pressure of the OB1 to 0
#         """
#         self.pressure.stop()

#     def close(self):
#         """
#         Performs shut down operations on voltage box and
#         OB1 pressure system
#         """
#         self.pressure.close()
#         self.voltage.close()
