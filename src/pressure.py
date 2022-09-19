import sys
sys.path.append("C:/Users/19199/Desktop/automated-sca/flow_controller")
from time import sleep

from OB1 import OB1

class Pressure:
  def __init__(self):
    self.pcontroller = OB1(calibrate=False)
    # TODO: load these from a file
    self.inPressure = -80
    self.eqPressure = 0
    self.outPressure = 80

  def calibrate(self):
    self.pcontroller.calibrate(save=True)

  def calibPressureValues(self, inPressure: float, eqPressure: float, outPressure: float):
    self.inPressure = inPressure
    self.eqPressure = eqPressure
    self.outPressure = outPressure

  def inThenHold(self):
    # TODO: don't hard-code channel as 4 (maybe)
    self.pcontroller.set_pressure(4, self.inPressure)
    sleep(1)
    self.pcontroller.set_pressure(4, self.eqPressure)

  def dispense(self):
    self.pcontroller.set_pressure(4, self.outPressure)
    sleep(2)
    self.pcontroller.set_pressure(4, self.eqPressure)

  def saveAndSetEq(self, eqP: float):
    self.eqPressure = eqP
    self.pcontroller.set_pressure(4, self.eqPressure)

  def stop(self):
    # Set pressure to equilibrium pressure so nothing is drawn in or dispensed
    self.pcontroller.set_pressure(4, 0)

  def close(self):
    self.pcontroller.close()
