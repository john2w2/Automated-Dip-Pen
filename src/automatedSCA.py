from re import S
import serial

from plate import Plate, Plate6, Plate12, Plate96, Plate384
from chip import Chip
from arm import Arm
from stage import Stage
# from printerHead import PrinterHead


class AutomatedSCA:
    """
    Top-level class to control movement of
    the printer head as well as printing

    Exposes low-level operations of the system: sucking in a sample,
        moving the head into a well, etc.

    We intend for these low-level operations to be combined into
        higher-level functions in microscopeDriver
    """
    def __init__(self, plateSize, numChan, chanDist, 
                priorPort: str = "COM4", arduinoPort="COM5"):
        """
        Initialize all devices for microscope
        Also starts z axis arm calibration TODO: I suggest doing this manually

        :param priorPort: COM port of stage, defaults to "COM4"
        :type priorPort: str, optional
        :param arduinoPort: COM port of arduino, defaults to "COM5"
        :type arduinoPort: str, optional
        :raises ConnectionError: when unable to connect to a device
        """
        # TODO: change chip parameters to just be chanDist
        self.chip: Chip = Chip(numChan=numChan, chanGapWidth=chanDist, chanWidth=0)

        if plateSize == 6:
            self.plate: Plate = Plate6()
        elif plateSize == 12:
            self.plate: Plate = Plate12()
        elif plateSize == 96:
            self.plate: Plate = Plate96()
        else:
            self.plate: Plate = Plate384()

        self.currentSample: str = self.chip.CHAN_EMPTY  # what is currently in the head

        # connecting to devices can throw a SerialException
        try:
            # connect to prior controller
            self.priorController = serial.Serial(priorPort, baudrate=9600, timeout=0.1)
            self.stage: Stage = Stage(plate=self.plate, chip = self.chip, priorController=self.priorController)
            print("prior")
            # so we can close priorController connecting to arm
            try:
                self.arm: Arm = Arm(arduinoPort=arduinoPort)
                print("arm")
            except serial.SerialException as err:
                self.priorController.close()
                raise ConnectionError(err)

            # self.printer: PrinterHead = PrinterHead(priorController=self.priorController)

        except serial.SerialException as err:
            raise ConnectionError(err)

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

    def moveChannelToCamNoLift(self, channelNum: int):
        """
        Moves the stage such that the camera displays the requested channel.
        Does not lift the arm before moving

        :param channelNum: 1-indexed number of channel to display
        :type channelNum: int
        """
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

    # def printSample(self, channelNum: int, save=True):
    #     """
    #     Applies a voltage to the printer head, printing a
    #     single cell. Also updates the stored contents of the chip. 
    #     Assumes the printer head is already in the correct position.

    #     ASSUME that sample is perfect

    #     :param channelNum: channel printer head is currently over, only 
    #     used to update stored contents of chip
    #     :type channelNum: int
    #     """
    #     if (save):
    #         self.chip.fillChannel(channelNum, self.currentSample)
    #     self.printer.printSingleDrop()

    def getSample(self, wellID: str):
        """
        Sucks in the sample that the printer head
        is submerged in, storing that sample as the
        microscope's current sample
        Assumes that the printer head is submerged in wellID
        :param wellID: the sample the head is submerged in. Only used to 
        update the contents of the printer head, does NOT move to wellID
        :type wellID: string
        """
        # self.printer.getSample()
        # update which sample is stored in the printer
        self.currentSample = wellID

    # def dispenseSample(self):
    #     """
    #     Applies a positive pressure, dispensing all of the currently
    #     held sample.
    #     """
    #     self.printer.dispenseSample()
    #     self.currentSample = self.chip.CHAN_EMPTY
    #     # self.currentSample = "dirty" ???
    #     # TODO: add cleaning feature

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
        # self.moveToSafePositions()
        self.arm.close()
        # self.printer.close()
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

    def getStageXY(self) -> tuple[int, int]:
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
        saves the current stage position as the position
        of the stage such that the center of the well
        is focused on the camera
        """
        # TODO: implement this soon using well center algo
        # self.stage.calibFirstWellCamPos(self.stage.getStageXY())
        xy = self.stage.getStageXY()           # Get the current XY
        saved = self.stage.calibFirstWellCamPos(xy)   # Save it in stage
        return saved

    def saveFiducialLocation(self):
        """
        saves the current stage position such that the fiducial marker (spot)
        is focused with the camera crosshair
        """
        xy = self.stage.getStageXY()
        saved = self.stage.calibFiducialCamPos(xy)
        return saved

    def savePenLocation(self):
        """
        saves the current stage position as the position
        of the stage such that the pen is focused on the camera
        """
        # self.stage.calibPenPos(self.stage.getStageXY())
        xy = self.stage.getStageXY()
        saved = self.stage.calibPenPos(xy)
        return saved

    def calibFirstChannelCam(self):
        """
        saves the current stage position as the
        position where first channel is lined up on + of camera
        """
        xy = self.stage.getStageXY()
        saved = self.stage.calibFirstChannelCamPos(xy)
        return saved
    
    # def calibVoltage(self, voltage: float):
    #     """
    #     Saves the voltage needed to print a single drop

    #     Reminder: we still need to use JetServer
    #     """
    #     # NOTE: right now voltage is triggered through JetServer,
    #     # so we aren't in control of the voltage from python
    #     # meaning this function might not be necessary

    #     raise NotImplementedError("printer head not implemented yet")

    # def calibPressureSystem(self):
    #     self.printer.calibPressureSystem()

    # def calibPressureValues(self, inP, eqP, outP):
    #     """
    #     Saves the pressure to suck in, the pressure to suck out,
    #     and the pressure to maintain equilibrium (holding fluid in place)
    #     """
    #     self.printer.calibPressureVals(inP, eqP, outP)
