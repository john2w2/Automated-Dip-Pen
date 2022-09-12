from flow_controller import OB1

class Pressure:
  def __init__(self):
    self.printer = OB1(calibrate=False)
    print(self.printer.get_pressure(4))
