class Chip:

    """
    This class represents the Chip used for experimentation

    :param numChan: Number of channels on the chip
    :type numChan: int, optional
    :param chanWidth: Width of a single channel (um)
    :type chanWidth: int, optional
    :param chanGapWidth: Width of the gap between 2 adjacent channels (um)
    :type chanGapWidth: int, optional
    :param chanContents: Description of each channel's contents
    :type chanContents: list[str], optional

    """

    CHAN_EMPTY: str = " "

    def __init__(self, numChan=40, chanWidth=100, chanGapWidth=160):
        """
        Constructor

        By default our chip has 40 channels
        """
        self.numChan = numChan
        self.chanWidth = chanWidth
        self.chanGapWidth = chanGapWidth
        self.chanContents = [Chip.CHAN_EMPTY for _ in range(self.numChan)]


    def getChannelContents(self, channelNum: int) -> str:
        assert (channelNum >= 1 and channelNum <= self.numChan)
        return self.chanContents[channelNum-1]

    def isEmpty(self, channelNum: int) -> bool:
        """Check if a channel is empty

        :param channelNum: Channel number
        :type channelNum: int
        :return: True if channel empty; False otherwise
        :rtype: bool
        """
        return self.getChannelContents(channelNum) == Chip.CHAN_EMPTY


    def fillChannel(self, channelNum: int, wellID: str):
        assert (channelNum >= 1 and channelNum <= self.numChan)
        if (not self.isEmpty(channelNum)):
            print("ERROR: This channel already holds a sample")
        else:
            self.chanContents[channelNum-1] = wellID\

    def getAllChannelContents(self):
        return self.chanContents

    def __str__(self):
        return (
            "Chip:\n"
            "Number of Channels: {numChan}\n"
        ).format(**self.__dict__)
