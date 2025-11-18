class Plate:
    # TODO: maybe store center-to-center distance instand of diameter
    """
    This class represents the Well Plate used for experimentation

    :param numRows: Number of rows on the plate, denoted by A, B, C, ...
    :type numRows: int, optional
    :param numCols: Number of columns on the plate, numbered 1, 2, 3...
    :type numCols: int, optional
    :param wellDiam: Diameter (in um) of a well
    :type wellDiam: int, optional
    :param wellDepth: Depth (in um) of a well
    :type wellDepth: int, optional

    """

    def __init__(self, numRows=8, numCols=12, diam=9000, depth=11000):
        """
        Constructor

        By default we use a standard 96-well plate
        """

        # NOTE: 1 mm = 1000 um, 1 cm = 10,000 um

        self.numRows = numRows
        self.numCols = numCols
        self.diam = diam
        self.depth = depth

class Plate6(Plate):
    """6 well plate"""
    def __init__(self):
        super().__init__(numRows=2, numCols=3, diam=39120, depth=17400)

class Plate12(Plate):
    """12 well plate"""
    def __init__(self):
        super().__init__(numRows=3, numCols=4, diam=22000, depth=18000)

class Plate96(Plate):
    """96 well palte"""
    def __init__(self):
        super().__init__(numRows=8, numCols=12, diam=9000, depth=11000)
    
class Plate384(Plate):
    """384 well plate"""
    def __init__(self):
        super().__init__(numRows=16, numCols=24, diam=4500, depth=10400)