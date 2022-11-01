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


    def getChannelContent(self, channelNum: int) -> str:
        """Return content (source well ID or CHAN_EMPTY) of specified channel

        :param channelNum: Channel number
        :type channelNum: int
        :return: Source well ID or CHAN_EMPTY
        :rtype: str
        """
        assert (channelNum >= 1 and channelNum <= self.numChan)
        return self.chanContents[channelNum-1]


    def isEmpty(self, channelNum: int) -> bool:
        """Check if a channel is empty

        :param channelNum: Channel number
        :type channelNum: int
        :return: True if channel empty; False otherwise
        :rtype: bool
        """
        return self.getChannelContent(channelNum) == Chip.CHAN_EMPTY


    def fillChannel(self, channelNum: int, wellID: str):
        assert (channelNum >= 1 and channelNum <= self.numChan)
        if (not self.isEmpty(channelNum)):
            print("ERROR: This channel already holds a sample")
        else:
            self.chanContents[channelNum-1] = wellID

    def getAllChannelContents(self):
        return self.chanContents.copy()

    def getAllEmptyChannels(self):
        emptyChannels = []
        for chan in range(1, self.numChan+1):
            if self.getChannelContent(chan) == self.CHAN_EMPTY:
                emptyChannels.append(chan)
        return emptyChannels


    def __str__(self):
        """Output textual representation of Chip

        :return: Textual representation of Chip
        :rtype: str
        """
        return (
            "Chip:\n"
            "Number of Channels: {numChan}\n"
        ).format(**self.__dict__)
