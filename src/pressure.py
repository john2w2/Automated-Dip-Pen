import sys
sys.path.append("C:/Users/19199/Desktop/automated-sca/flow_controller")
from time import sleep

from OB1 import OB1


class Pressure:
  def __init__(self):
    self.pcontroller = OB1(calibrate=False)
    self.inPressure = -80
    self.eqPressure = 0
    self.outPressure = 80

  def calibrate(self):
    self.pcontroller.calibrate(save=True)

  def inThenHold(self):
    # TODO: don't hard-code channel as 4 (maybe)
    self.pcontroller.set_pressure(4, self.inPressure)
    sleep(1)
    self.pcontroller.set_pressure(4, self.eqPressure)

  def blowOut(self):
    self.pcontroller.set_pressure(4, self.outPressure)
    sleep(2)
    self.pcontroller.set_pressure(4, self.eqPressure)

  def savePressureVals(self, inP: int, eqP: int, outP: int):
    self.inPressure = inP
    self.eqPressure = eqP
    self.outPressure = outP

  def stop(self):
    self.pcontroller.set_pressure(4, 0)


  def close(self):
    self.pcontroller.close()