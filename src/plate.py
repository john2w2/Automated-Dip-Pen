class Plate:
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
