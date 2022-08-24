class Screw:

    def __init__(self, numStarts=2, tpi=13):
        self.numStarts = numStarts
        self.tpi = tpi

    def getLead(self):
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
