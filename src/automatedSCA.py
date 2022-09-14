from re import S
import serial

from plate import Plate
from chip import Chip
from arm import Arm
from stage import Stage
from printerHead import PrinterHead
# from printer import Printer


class AutomatedSCA:
    """
    Top-level class to control movement of
    the printer head as well as printing

    Exposes low-level operations of the system: sucking in a sample,
        moving the head into a well, etc.

    We intend for these low-level operations to be combined into
        higher-level functions in microscopeDriver
    """

    def __init__(self, priorPort: str = "COM6", arduinoPort="COM7"):
        # NOTE: serial connection to prior box (usually COM6, stage port)
        # will have to be made here and passed down to movement
        # and printer head
        # reason: printer head needs to send TTL command though prior box
        # in order to print a drop
        """
        Initialize all devices for microscope
        Also starts z axis arm calibration TODO: I suggest doing this manually

        :param priorPort: COM port of stage, defaults to "COM6"
        :type priorPort: str, optional
        :param arduinoPort: COM port of arduino, defaults to "COM7"
        :type arduinoPort: str, optional
        :raises ConnectionError: when unable to connect to a device
        """
        # TODO: don't hardcode numChan, numRows, numCols
        self.chip: Chip = Chip(numChan=40)
        self.plate: Plate = Plate(numRows=8, numCols=12)

        self.currentSample: str = self.chip.CHAN_EMPTY  # what is currently in the head

        # connecting to devices can throw a ConnectionError
        # connect to low-level devices
        try:
            # connect to prior controller
            self.priorController = serial.Serial(
                priorPort, baudrate=9600, timeout=0.1)
            # start up printer head
            self.printer: PrinterHead = PrinterHead(
                priorController=self.priorController)
            # TODO: prior controller  take care of printing
            self.stage: Stage = Stage(
                plate=self.plate, chip=self.chip, priorController=self.priorController)

            # so we can close priorController if this fails
            # TODO: why nested?
            try:
                self.arm: Arm = Arm(arduinoPort=arduinoPort)
            except ConnectionError as err:
                self.priorController.close()
                raise ConnectionError(err)

        except ConnectionError as err:
            raise ConnectionError(err)

        # TODO: still on the fence about whether or not to run calibrateArm on startup
        # self.calibrateArm()
        # TODO: put all calibration stuff here later

    # ======================================= #
    #                low-level                #
    # ======================================= #

    def interruptArm(self):
        """
        Sends an interrupt command to the arduino to stop its movement
        immediately
        """
        self.arm.interruptArm()


    # TODO: what is this being used? Can we place with absolute distance (in um?)
    def moveStageByX(self, steps: int):
        """
        Moves the stage by steps steps. Intended
        to be for testing printing drops
        """

        self.arm.moveZUpPos()
        self.stage.moveXInUM(steps * self.stage.stepSize)

    def moveChannelToCam(self, channelNum: int):
        """
        Moves stage such that camera displays the requested channel

        :param channelNum: 1-index number of channel to display
        :type channelNum: int
        """
        self.arm.moveZUpPos()
        self.stage.moveChannelToCam(channelNum)

    def movePrinterIntoWell(self):
        """
        Moves the printer head down into well pos, assuming the stage
        had already positioned the printer ehad over the well
        """
        self.arm.moveZWellPos()

    def movePrinterOverWell(self, wellID: str):
        """
        Moves the printer head above the specified well, does NOT move down into well
        Does nothing if z-axis arm isn't calibrated

        :param wellID: ID of well to move over
        :type wellID: str
        """
        self.arm.moveZUpPos()
        self.stage.moveWellToPrinter(wellID)

    def movePrinterOverChannel(self, channelNum: int):
        """moves the printer head vertically over channelNum
        Does NOT move the printer head down to the channel

        :param channelNum: channel to move over
        :type channelNum: int
        """
        self.arm.moveZUpPos()
        self.stage.moveChannelToPrinter(channelNum)

    def movePrinterDownToChannel(self):
        """
        moves the head down to it's above-channel position
        Does not move on the xy plane, must be over the chip
        or will probably break
        """
        self.arm.moveZChannelPos()

    def moveToChannelNoLift(self, channelNum: int):
        """unsafe function
        Moves the printer head above the specified channel
        without lifing beforehand. Intended to be used
        for printing the same sample to multiple channels
        with no other operations in between

        ASSUME printer already down

        :param channelNum: channel to move to
        :type channelNum: int
        """
        # this movement is unsafe because printer head is not lifted
        # before moving and head remains down when function finishes
        self.stage.moveChannelToPrinter(channelNum)

    def moveArmToUp(self):
        """
        moves the printer arm to its default up position
        """
        self.arm.moveZUpPos()

    def printSample(self, channelNum: int):
        """
        Applies a voltage to the printer head, printing a
        single cell. Assumes the printer head
        is already in the correct position

        ASSUME that sample is perfect

        :param channelNum: channel printer head is currently over
        :type channelNum: int
        """

        self.chip.fillChannel(channelNum, self.currentSample)
        self.printer.printSingleDrop()

    def getSample(self, wellID: str):
        """
        Sucks in the sample that the printer head
        is submerged in, storing that sample as the
        microscope's current sample
        Assumes that the printer head is submerged in wellID
        :param wellID: the sample the head is submerged in
        :type wellID: string
        """
        self.printer.getSample()
        # update which sample is stored in the printer
        self.currentSample = wellID

    def dispenseSample(self):
        """
        Applies a positive pressure, dispensing all of the currently
        held sample.
        """
        self.printer.dispenseSample()
        self.currentSample = self.chip.CHAN_EMPTY
        # self.currentSample = "dirty" ???
        # TODO: add cleaning feature

    def moveToSafePositions(self):
        # TODO: add a function in movement/arm to move up to a
        # much higher (safer) position than the default up position
        # TODO: see if we end up using this?
        """
        Moves the printer arm to its up position and
        moves the stage such that the first well is under the printer
        This is intended to be issued after an interrupt command to
        put the device in some "safe" state where the needle can't be broken
        """

        self.arm.moveToOrigin()
        self.stage.moveToWell("A1")

    # ======================================= #
    #             helper / utility            #
    # ======================================= #
    def close(self):
        """
        closes all connected devices
        Should be called before program ends to free the stage and arduino
        """
        self.moveToSafePositions()
        self.arm.close()
        self.priorController.close()
        # self.pressure.close()

    def getEmptyChannels(self):
        """
        returns a list of channels that have not had anything printed to them
        """
        return self.chip.getAllEmptyChannels()


    # TODO: these 2 methods bother me, don't do anything different than original
    def getAllChannelContents(self):
        return self.chip.getAllChannelContents()

    def getStageXY(self):
        return self.stage.getStageXY()

    # ======================================= #
    #               calibration               #
    # ======================================= #

    def calibrateArm(self):
        """
        Calibrates the z-axis arm's 0 position
        Must be called before the arm is moved

        TODO: names might change once Y Arm added (calibrateZArm or something)
        OR just say this is for all relevant arm motors
        """
        self.arm.calibrateOrigin()

    def resetStageOrigin(self):
        # TODO: set current position of stage as 0,0 (assuming user moved to bottom right)
        """
        Resets the 0,0 position of stage
        """
        self.stage.calibOrigin()

    def calibPrinterOffset(self, offsetX: int, offsetY: int):
        """
        Saves the offset of the printer head
        Offset values come from GUI calibration method

        :param offsetX: distance (in steps) stage has to move to put first
            channel under printer head, starting from first channel
            being focused on cross of camera (along x axis)
            offsetX = printerDropX - focusedDropX
        :type offsetX: int
        :param offsetY: distance (in steps) stage has to move to put first
            channel under printer head, starting from first channel
            being focused on cross of camera (along x axis)
            offsetY = printerDropY - focusedDropY
        :type offsetY: int
        """
        self.stage.calibPrinterOffset(offsetX, offsetY)

    def saveFirstWellLocation(self):
        """
        saves the current stage position where
        the printer head is directly above the first well
        """
        # TODO: implement this soon using offset and well center algo
        raise NotImplementedError(
            " saving first well location not yet implemented")

    def calibFirstChannelCam(self):
        """
        saves the current stage position as the
        position where first channel is lined up on + of camera
        """
        self.stage.calibFirstChannelCamPos()

    def calibVoltage(self, voltage: float):
        """
        Saves the voltage needed to print a single drop

        Reminder: we still need to use JetServer
        """
        # NOTE: right now voltage is triggered through JetServer,
        # so we aren't in control of the voltage from python
        # meaning this function might not be necessary

        raise NotImplementedError("printer head not implemented yet")

    def calibPressureSystem(self):
        self.printer.calibPressureSystem()

    def calibPressureValues(self, inP, eqP, outP):
        """
        Saves the pressure to suck in, the pressure to suck out,
        and the pressure to maintain equilibrium (holding fluid in place)
        """
        self.printer.calibPressureVals(inP, eqP, outP)
