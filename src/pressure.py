import sys
# sys.path.append("C:/Users/19199/Desktop/automated-sca/flow_controller")
import numpy as np
from time import sleep

from elveflow_ob1 import ElveflowOB1
from deviceInterfaces.pressure_system import PressureSystem

DEFAULT_CHANNEL: int = 3

class Pressure:
  def __init__(self):
    self.pcontroller: PressureSystem = ElveflowOB1()
    # TODO: load these from a file
    self.inPressure = -80
    self.eqPressure = 0
    self.outPressure = 80
    self.inTime = 3
    self.outTime = 3
    self.offset = 0.0
    self.lastReqPressure = 0.0

  def calibrate(self):
    self.pcontroller.calibrate()

  def calibPressureValues(self, inPressure: float, eqPressure: float, outPressure: float):
    self.inPressure = inPressure
    self.eqPressure = eqPressure
    self.outPressure = outPressure

  def calibDurations(self, inPTime: float, outPTime: float):
    self.inTime = inPTime
    self.outTime = outPTime

  def inThenHold(self):
    # TODO: don't hard-code channel as 4 (maybe)
    self.pcontroller.set_pressure(self.inPressure + self.offset, channel=DEFAULT_CHANNEL)
    sleep(self.inTime)
    self.pcontroller.set_pressure(self.eqPressure + self.offset, DEFAULT_CHANNEL)
    self.lastReqPressure = self.eqPressure

  def dispense(self):
    self.pcontroller.set_pressure(self.outPressure + self.offset, DEFAULT_CHANNEL)
    sleep(self.outTime)
    self.pcontroller.set_pressure(self.eqPressure + self.offset, DEFAULT_CHANNEL)
    self.lastReqPressure = self.eqPressure

  def saveAndSetEq(self, eqP: float):
    self.eqPressure = eqP
    self.pcontroller.set_pressure(self.eqPressure + self.offset, DEFAULT_CHANNEL)
    self.lastReqPressure = self.eqPressure

  def recalibrateOffset(self):
    """
    Computes the difference between the (average) actual pressure
    and the requested pressure.
    That offset is then used when setting new values
    """
    self.pcontroller.set_pressure(self.lastReqPressure, DEFAULT_CHANNEL)
    print(f"Last requested is {self.lastReqPressure}")
    vals = []

    for _ in range(100):
      sleep(0.5)
      vals.append(self.pcontroller.get_pressure(DEFAULT_CHANNEL))
      print(vals[-1])

    self.offset = self.lastReqPressure - np.average(np.array(vals))

  def setSteady(self, steadyP):
    self.pcontroller.set_pressure(steadyP + self.offset, DEFAULT_CHANNEL)
    self.lastReqPressure = steadyP

  def setToZero(self):
    self.setSteady(0.0)

  def stop(self):
    # Set pressure to equilibrium pressure so nothing is drawn in or dispensed
    self.pcontroller.set_pressure(DEFAULT_CHANNEL, 0)

  def close(self):
    self.pcontroller.close()
