from multiprocessing.sharedctypes import Value
from threading import Thread
import string
from time import sleep
from automatedSCA import AutomatedSCA


class MicroscopeDriver:
    """
    Class for sending commands to the microscope, starting a thread
    for the ones involving movement as to not freeze the GUI.
    Combines microscope functions into high level behaviors.
    It also exposes a few low-level features for sanity checking.
    This class will assume that multiple threaded operations will not be issued in parallel.
    It also checks if inputs are valid, raising ValueErrors if they aren't.

    NOTE: callers of (most of these) functions should disable the appropriate
        buttons and pass a callback to re-enable those buttons. That
        callback is called when the function returns
    """

    def __init__(self, priorPort: str, arduinoPort: str, cb,
                plateSize: int =96, numChan:int = 40, chanDist:int = 260
    ):
        """
        Instantiates the microscope, connecting to all devices

        :param priorPort: COM port of prior controller (used for stage and JetServer voltage)
        :type priorPort: str
        :param arduinoPort: COM port of arduino
        :type arduinoPort: str
        :param cb: callback function to call when this method finishes running
        :type cb: function
        """

        try:
            self.microscope: AutomatedSCA = AutomatedSCA(
                priorPort=priorPort, arduinoPort=arduinoPort,
                plateSize=plateSize, numChan=numChan, chanDist=chanDist)
        except:
            raise ConnectionError
        self.stop_threads: bool = False

        # currently running thread
        self.currentThread: Thread = None
        # so we can block this interrupt thread when we close
        self.interruptThread: Thread = None

        # which wells contain ethanol (cleaning solution)
        self.ethanolWells = []
        # which wells have samples to use for experiment
        self.sampleWells = []

        # enable GUI buttons
        cb()

    # =======================================
    #           calibration functions       #
    # =======================================

    def calibrateZArm(self, cb):
        """Starts a thread which calibrates the z-axis arm

        :param cb: callback function used to reenable buttons on UI
        :type cb: function
        """
        t: Thread = Thread(target=self.__calibrateZArm, args=[cb])
        self.currentThread = t
        t.start()

    def __calibrateZArm(self, cb):
        """Calibrates the z-axis arm of printer

        :param cb: callback function used to reenable buttons on UI
        :type cb: function
        """
        self.microscope.calibrateArm()
        cb()

    def calibrateStage(self):
        """
        Starts a thread that resets the stage's internal positioning
        """
        self.microscope.resetStageOrigin()

    def recalibrateOB1(self):
        """
        Recalibrates the OB1 pressure system. This recalibration is 
        asynchronous and we can't really get a signal when it completes.
        """
        self.microscope.printer.calibPressureSystem()

    def saveFirstChannelCamPos(self):
        """Saves the current stage position as the 
        position such that the first channel is focused
        on the + of the camera
        """
        self.microscope.calibFirstChannelCam()

    def saveFirstWellCamPos(self):
        """Saves the current stage position as the 
        position such that the center of the first well
        is focused on the + of the camera
        """
        self.microscope.saveFirstWellLocation()


    def saveOffset(self, offsetX: int, offsetY: int):
        """
        Saves offset between first channel and printer head as
        (offsetX, offsetY)
        These values should be computed within a GUI function by
        having the user print a drop, then focus that drop on the microscope,
        calculating the difference of those two positions.

        :param offsetX: difference between printing position x and focused drop x
        :type offsetX: int
        :param offsetY: difference between printing position y and focused drop y
        :type offsetY: int
        """

        self.microscope.calibPrinterOffset(offsetX, offsetY)

    def saveVoltage(self, voltage: float):
        """saves the given voltage as the one
        that works for printing single cells

        :param voltage: voltage used to print a single cell
        :type voltage: float
        """
        # NOTE: we might not save voltage since we're working with
        # JetServer, which controls the voltage

        raise NotImplementedError()

    def savePressures(self, inPressure: float, eqPressure: float,  outPressure: float):
        """
        Saves the pressure values as the ones used for experimenting

        :param eqPressure: pressure to hold a sucked in sample in equilibrium
        :type eqPressure: float
        :param inPressure: pressure to suck in a sample
        :type inPressure: float
        :param outPressure: pressure to dispense all of a sample
        :type outPressure: float
        """

        self.microscope.calibPressureValues(inP=inPressure, eqP=eqPressure, outP=outPressure)

    def saveSafeZPosition(self, mm: float):
        """Saves mm as the distance from the top limit switch to 
        a safe position of the arm

        :param mm: Distance (in mm) from the top limit switch
        :type mm: float
        """

        if mm > 0: raise ValueError("Distance must be negative. You cannot move above the top limit switch")
        
        self.microscope.arm.saveZUpPos(mm)

    def saveChipZPosition(self, mm:float):
        """Saves mm as the distance from the top limit switch to
        the 'above chip' position

        :param mm: Distance (in mm) from the top limit switch 
        :type mm: float
        """

        if mm > 0: raise ValueError("Distance must be negative. You cannot move above the top limit switch")
        self.microscope.arm.saveZChipPos(mm)

    def saveWellZPosition(self, mm:float):
        """Saves mm as the distance from the top limit switch to
        the 'in well' position

        :param mm: Distance (in mm) from the top limit switch 
        :type mm: float
        """

        if mm > 0: raise ValueError("Distance must be negative. You cannot move above the top limit switch")
        self.microscope.arm.saveZWellPos(mm)


    def saveEthanolWells(self, wells: list[str]):
        """Saves which wells contain cleaning solution

        :param wells: list of wells containing ethanol
        :type wells: list[str]
        """
        if not self.checkWellsValid(wells):
            raise ValueError("wells aren't formatted correctly")

        self.ethanolWells = wells

    def saveSampleWells(self, wells: list[str]):
        # NOTE: this may not be necessary. If we remove it,
        # make sure to update all checks using it (if not wellID in this.sampleWells ...)
        """
        Saves which wells contain samples to be used
        for the experiment

        :param wells: list of wells that hold ethanol
        :type wells: list[str]
        :raises ValueError: if wells is not entirely properly formatted
        """
        if not self.checkWellsValid(wells):
            raise ValueError("wells aren't formatted correctly")

        self.sampleWells = wells

    # ========================================= #
    #               sanity checks               #
    # ========================================= #
    # So the user can see that the calibration was correct
    # without breaking anything (hopefully)

    def testOverWell(self, wellID: str, cb):
        """
        Moves the printer head to be just above a well to
        see if well positions are calibrated correctly

        :param wellID: well to move over
        :type wellID: str
        :param cb: callback to reenable buttons on ui
        :type cb: function
        :raises ValueError: if wellID isn't a valid well ID
        """
        if not self.checkWellsValid([wellID]):
            cb()
            raise ValueError(f"{wellID} is not a valid well ID")

        t: Thread = Thread(target=self.__testOverWell, args=[wellID, cb])
        self.currentThread = t
        t.start()

    def __testOverWell(self, wellID: str, cb):
        # move up, move to well
        self.microscope.moveArmToUp()
        if self.__checkInterrupt(cb):return

        self.microscope.movePrinterOverWell(wellID)
        cb()

    def testOverChannel(self, channelNum: int, cb):
        """Moves head just above a channel to see
        if printer offset is calibrated correctly

        :param channelNum: channel to move over
        :type channelNum: int
        :param cb: callback to reenable buttons on ui
        :type cb: function
        :raises: ValueError if channelNum isn't a valid channel number
        """
        if not self.checkChannelsValid([channelNum]):
            cb()
            raise ValueError(f"{channelNum} isn't a valid channel number")

        channelNum = int(channelNum)

        t: Thread = Thread(target=self.__testOverChannel, args=[channelNum, cb])
        self.currentThread = t
        t.start()

    def __testOverChannel(self, channelNum: int, cb):
        self.microscope.moveArmToUp()
        if self.__checkInterrupt(cb):return

        self.microscope.movePrinterOverChannel(channelNum)
        if self.__checkInterrupt(cb):return

        self.microscope.movePrinterDownToChannel()
        cb()

    def testGrabSample(self, wellID: str, cb):
        # TODO: this is probably not necessary, figured I might just have it
        # here for completion
        """
        Grabs the sample from wellID
        """
        self.grabSample(wellID, cb)


    def testPrintDropToChan(self, channelNum: int, cb):
        """
        Prints a single drop to the specified channel.
        - throws exception if nothing in printer head
        Intended to be used with a waste slide
        for checking if printing is working. Using
        this on one of the extra channels on chip will
        tell us if offset calibration + first channel calibration is good
        NOTE: since this is for sanity checking a single behavior, it doesn't
        include the step where we suck in a sample. There is another sanity check
        for that that should have been run before this one

        :param cb: callback to reenable buttons on ui
        :type cb: function
        :param channelNum: channel to print to (on empty slide, this is where channel would be)
        :type channelNum: int
        :raises ValueError: if nothing is held in printer head
        """
        if self.microscope.currentSample == self.microscope.chip.CHAN_EMPTY:
            cb()
            raise ValueError("no sample held in printer")

        if not self.checkChannelsValid([channelNum]):
            cb()
            raise ValueError("channel number is invalid")

        channelNum = int(channelNum)

        t: Thread = Thread(target=self.__testPrintDropToChannel, args=[channelNum, cb])
        self.currentThread = t
        t.start()

    def __testPrintDropToChannel(self, channelNum: int, cb):
        self.microscope.moveArmToUp()
        if self.__checkInterrupt(cb):return

        self.microscope.movePrinterOverChannel(channelNum)
        if self.__checkInterrupt(cb):return

        self.microscope.movePrinterDownToChannel()
        if self.__checkInterrupt(cb):return

        self.microscope.printSample(channelNum)
        if self.__checkInterrupt(cb):return

        self.microscope.moveArmToUp()
        cb()

    def testPrintMultipleDrops(self, drops: int, cb):
        # TODO: maybe remove channel requirement and make it drop in place
        # requires: printer head is above the waste slide
            # move down, print drops in a row, move up, show first drop on cam 
            # show first drop = firstDropLoc - offset (I'm pretty sure)
        """Tests printing multiple drops of currently held
        sample to the current position of the printer head.
        Used to test
        - first channel calibration
        - printer head offset calibration
        Intended to be used with a waste slide or one
        of the unneeded channels on chip.
        NOTE: this is testing just the behavior of printing multiple drops,
        so it doesn't include the step of sucking in the sample beforehand.
        That should have been tested earlier

        :param drops: number of drops to print on the slide
        :type drops: int
        :param cb: callback to reenable buttons on ui
        :type cb: function
        :raises ValueError: if no sample held in printer head
        :raises ValueError: if channelNum isn't a valid channel
        :raises ValueError: if number of drops to print isn't in range [1,10]
        """
        if self.microscope.currentSample == self.microscope.chip.CHAN_EMPTY:
            cb()
            raise ValueError("nothing held in printer head")

        if drops < 1 or drops > 10:
            cb()
            raise ValueError("number of drops must be in range [1,10]")

        t: Thread = Thread(target=self.__testPrintMultipleDrops, args=[
                           drops, cb])
        self.currentThread = t
        t.start()

    def __testPrintMultipleDrops(self, drops: int, cb):
        # TODO: maybe remove channel requirement and make it drop in place
        # requires: printer head is above the waste slide
            # move down, print drops in a row, move up, show first drop on cam 
            # show first drop = firstDropLoc - offset (I'm pretty sure)

        # TODO: have a stage command that can move horizontally slightly
        self.microscope.moveArmToUp()
        if self.__checkInterrupt(cb): return

        self.microscope.movePrinterDownToChannel()
        if self.__checkInterrupt(cb): return

        firstDrop = self.microscope.getStageXY()

        for _ in range(drops):
            if self.__checkInterrupt(cb): return
            self.microscope.printSample(1, save=False) # doesn't actually update channel 1
            if self.__checkInterrupt(cb): return
            self.microscope.stage.moveXInUM(-500) # something like this, move 500 um to the right
        if self.__checkInterrupt(cb): return

        self.microscope.moveArmToUp()
        if self.__checkInterrupt(cb): return

        self.microscope.stage.moveDropToCam(dropLoc=firstDrop)
        cb()

    # ================ low level functions ==================
    # these low level functions are intended to provide the user with a small amount
    # of control to continue doing sanity checks, or to do small stuff (like focusing a channel)
    # some of these will also be called by high level functions for cleanup / setup

    def moveToZRelInUM(self, um, cb):
        """_summary_

        :param um: _description_
        :type um: _type_
        :param cb: _description_
        :type cb: function
        """

        t: Thread = Thread(target=self.__moveToZRelInUM, args=[um, cb])
        self.currentThread = t
        t.start()

    def __moveToZRelInUM(self, um, cb):
        self.microscope.arm.zmotor.moveToZRelInUM(um)
        cb()

    def moveToZAbsoluteInUM(self, um, cb):
        """_summary_

        :param um: _description_
        :type um: _type_
        :param cb: _description_
        :type cb: function
        """
        if (um > 0):
            cb() 
            raise ValueError("Position must be negative")
            
        t: Thread = Thread(target=self.__moveToZAbsoluteInUM, args=[um, cb])
        self.currentThread = t
        t.start()

    def __moveToZAbsoluteInUM(self, um, cb):
        self.microscope.arm.zmotor.moveToZInUM(um)
        cb()

    def moveToZInSteps(self, steps, cb):
        """_summary_

        :param steps: _description_
        :type steps: _type_
        :param cb: _description_
        :type cb: function
        """
        t: Thread = Thread(target=self.__moveToZInSteps, args=[steps, cb])
        self.currentThread = t
        t.start()

    def __moveToZInSteps(self, steps, cb):
        self.microscope.arm.zmotor.moveToZInSteps(steps)
        cb()

    def moveDropToCam(self, dropLoc: tuple[int, int], cb):
        """
        Moves the stage by subtracting offset from the current position.
        Intended to be used to show a drop on the camera.

        :param dropX: x location of drop in steps
        :type dropX: int
        :param dropY: y location of drop in steps
        :type dropY: int
        """

        # start thread
        t: Thread = Thread(target=self.__moveDropToCam, args=[dropLoc, cb])
        self.currentThread = t
        t.start()

    def __moveDropToCam(self, dropLoc: tuple[int, int], cb):
        # self.microscope.moveArmToUp()
        # if self.__checkInterrupt(cb):return

        self.microscope.stage.moveDropToCam(dropLoc=dropLoc)
        cb()

    def printToCam(self, ref, cb):
        """_summary_

        :param cb: _description_
        :type cb: function
        """
        t: Thread = Thread(target=self.__printToCam, args=[ref, cb])
        self.currentThread = t
        t.start()

    def __printToCam(self, ref, cb):
        if self.__checkInterrupt(cb): return

        self.microscope.stage.camToPrinter()
        if self.__checkInterrupt(cb): return

        self.microscope.printer.printSingleDrop()
        if self.__checkInterrupt(cb): return

        dropLoc = self.microscope.getStageXY()
        ref.append(dropLoc)
        if self.__checkInterrupt(cb): return

        self.microscope.stage.moveDropToCam(dropLoc=dropLoc)
        if self.__checkInterrupt(cb): return

        cb()

    def movePrinterOverWell(self, wellID: str, cb):
        """
        Moves the printer over the specified well. 
        
        :param wellID: The well to move above
        :type wellID: str
        :param cb: callback function that is called when thread finishes
        :type cb: function        
        """
        if not self.checkWellsValid([wellID]):
            raise ValueError(f"{wellID} is not a valid well")

        t: Thread = Thread(target=self.__movePrinterOverWell, args=[wellID, cb])
        self.currentThread = t
        t.start()
        
    def __movePrinterOverWell(self, wellID: str, cb):
        self.microscope.moveArmToUp()
        if self.__checkInterrupt(cb): return

        self.microscope.movePrinterOverWell(wellID=wellID)
        cb()

    def movePrinterIntoWell(self, cb):
        """Moves the printer head down to its 'in well' position
            Assumes that the printer head is already lined up with the well;
            does not move stage.
        """
        t: Thread = Thread(target=self.__movePrinterIntoWell, args=[cb])
        self.currentThread = t
        t.start()

    def __movePrinterIntoWell(self, cb):
        self.microscope.movePrinterIntoWell()
        cb()
    
    def movePrinterToChip(self, cb):
        """Moves the printer head down to its 'over chip' position.
            Assumes that the printer head is already above the chip;
            does not move stage.
        """

        t:Thread = Thread(target= self.__movePrinterToChip, args=[cb])
        self.currentThread = t 
        t.start()

    def __movePrinterToChip(self, cb):
        self.microscope.movePrinterDownToChannel()
        cb()

    def printDropNoMove(self, cb):
        """ Applies a single voltage to the printer head, triggering jetserver. 
        Does not move the arm anywhere, and doesn't move the stage.

        :param cb: callback function that is called when function ends
        :type cb: function
        """
        t: Thread = Thread(target=self.__printDropNoMove, args=[cb])
        self.currentThread = t
        t.start()

    def __printDropNoMove(self, cb):
        self.microscope.printer.printSingleDrop()
        cb()

    def movePrinterOverChannel(self, channelNum:int, cb):
        """Moves the printer head over channelNum.
        Does not move the arm down to the channel

        :param channelNum: the channel to move over
        :type channelNum: int
        :param cb: _description_
        :type cb: function
        """

        if not self.checkChannelsValid([channelNum]):
            raise ValueError(f"{channelNum} not a valid channel")

        t:Thread = Thread(target=self.__movePrinterOverChannel, args=[channelNum, cb])
        self.currentThread = t
        t.start()

    def __movePrinterOverChannel(self, channelNum, cb):
        self.microscope.moveArmToUp()
        if self.__checkInterrupt(cb): return

        self.microscope.movePrinterOverChannel(channelNum=channelNum)
        if self.__checkInterrupt(cb): return

        cb()

    def moveArmToUp(self, cb):
        """_summary_

        :param cb: _description_
        :type cb: function
        """
        t:Thread = Thread(target=self.__moveArmToUp, args=[cb])
        self.currentThread = t
        t.start()

    def __moveArmToUp(self, cb):
        self.microscope.moveArmToUp()
        cb()

    def grabSampleNoMove(self, cb):
        """Sucks in with the printer head. 
        Assumes that the printer head is already submerged in solution

        :param cb: callback function that is called when thread finishes
        :type cb: function
        """

        t:Thread = Thread(target=self.__grabSampleNoMove, args=[cb])
        self.currentThread = t
        t.start()
    
    def __grabSampleNoMove(self, cb):
        # TODO: find better well id to put instead of A1
        self.microscope.getSample("A1")
        cb()

    def focusChannel(self, channelNum: int, cb):
        """Starts a thread that: focuses the given channel on the camera display

        :param channelNum: number of channel to place
        :type channelNum: _type_
        :param cb: callback function used to reenable buttons on UI
        :type cb: function
        """
        if not self.checkChannelsValid([channelNum]):
            cb()
            raise ValueError("channelNum isn't valid")

        channelNum = int(channelNum)

        t: Thread = Thread(target=self.__focusChannel, args=[channelNum, cb])
        self.currentThread = t
        t.start()

    def __focusChannel(self, channelNum: int, cb):
        """Focuses the given channel on the microscope, calling
           cb when done

        :param channelNum: channel to focus on camera
        :type channelNum: int
        :param cb: callback function used to reenable buttons on UI
        :type cb: function
        """
        self.microscope.moveArmToUp()
        if self.__checkInterrupt(cb): return
        self.microscope.moveChannelToCam(channelNum)
        cb()

    def focusChannelNoLift(self, channelNum: int, cb):
        """Focuses the given channel on the microscope without
        lifting the arm beforehand. 

        :param channelNum: channel number to focus on camera
        :type channelNum: int
        :param cb: callback function that is called when focusing is done
        :type cb: function
        """
        if not self.checkChannelsValid([channelNum]):
            cb()
            raise ValueError("channelnum isn't valid")
        
        channelNum = int(channelNum)

        t: Thread = Thread(target=self.__focusChannelNoLift, args=[channelNum, cb])
        self.currentThread = t
        t.start()

    def __focusChannelNoLift(self, channelNum: int, cb):
        if self.__checkInterrupt(cb): return
        self.microscope.moveChannelToCamNoLift(channelNum=channelNum)
        cb()

    def chanToPrinterNoLift(self, channelNum: int, cb):
        """_summary_

        :param channelNum: _description_
        :type channelNum: int
        :param cb: _description_
        :type cb: function
        """
        if not self.checkChannelsValid([channelNum]):
            cb()
            raise ValueError("channelnum isn't valid")
        
        channelNum = int(channelNum)

        t: Thread = Thread(target=self.__chanToPrinterNoLift, args=[channelNum, cb])
        self.currentThread = t
        t.start()

    def __chanToPrinterNoLift(self, channelNum: int, cb):
        if self.__checkInterrupt(cb): return
        self.microscope.moveToChannelNoLift(channelNum=channelNum)
        cb()

    def printSampleToChannel(self, wellID: str, channelNum: int, cb):
        """ Sucks in the sample in wellID, then
        prints a single drop to the specified channel
        Cleans out the head when done. Also cleans out head
        if a sample from wellID isn't in the head at the start
        of the function

        :param wellID: well to get a sample from
        :type wellID: string
        :param channelNum: channel to print to
        :type channelNum: int
        :param cb: callback to reenable buttons on ui
        :type cb: function
        :raises ValueError: if nothing is held in printer head
        """
        if not self.checkChannelsValid([channelNum]):
            cb()
            raise ValueError("channelNum is not valid")

        channelNum = int(channelNum)

        if not (channelNum in self.microscope.getEmptyChannels()):
            cb()
            raise ValueError(f"channel {channelNum} is not empty")

        if not self.checkWellsValid([wellID]):
            cb()
            raise ValueError(f"{wellID} is not a valid well ID")

        # TODO: uncomment if we want this feature
        # if not (wellID in self.sampleWells):
        #     cb()
        #     raise ValueError(f"{wellID} doesn't have any sample in it")

        t: Thread = Thread(target=self.__printSampleToChannel, args=[wellID, channelNum, cb])
        self.currentThread = t
        t.start()

    def __printSampleToChannel(self, wellID: str, channelNum: int, cb):
        # since we call grabsample, we don't want it to call the actual cb preemptively
        def fakeCB(): x = 3

        self.microscope.moveArmToUp()
        if self.__checkInterrupt(cb): return

        self.__grabSample(wellID, fakeCB)
        if self.__checkInterrupt(cb): return

        self.microscope.movePrinterOverChannel(channelNum)
        if self.__checkInterrupt(cb): return

        self.microscope.movePrinterDownToChannel()
        if self.__checkInterrupt(cb): return

        self.microscope.printSample(channelNum)
        if self.__checkInterrupt(cb): return

        self.microscope.moveArmToUp()
        cb()

    def resetToSafeState(self):
        """
        Moves the microscope components back to a safe state
        - Arm is in raised position
        - stage is centered to show first channel
        # TODO: should also set pressure to 0, voltage to OFF
        """
        # TODO: arm needs another position (safeup)
        # TODO: this is also blocking, will want to thread it (maybe)
        self.microscope.moveArmToUp()
        # self.microscope.movePrinterOverWell("A1")

    def interrupt(self, cb):
        # TODO: right now this is blocking, will pause GUI
        # threading this may be weird... or maybe not I have to think about it

        # with the way the code is set up now, blocking is necessary
        # when the first thread sees an interrupt, it will call cb() and return,
        # which means buttons will be enabled while this interrupt command does things.
        # If this function is unthreaded, GUI will freeze until this function ends, preventing
        # the client from pressing those unsafe buttons while this is running
        """
        Interrupt the movement of the microscope, moving back to safe positions when done
        - Stage finishes previously issued command then stops
        - Arm stops immediately
        also note: cannot interrupt during the calibration that happens
        during the instantiation of microscope
        """

        self.stop_threads = True
        self.microscope.interruptArm()
        t: Thread = Thread(target=self.__interrupt, args=[cb])
        self.interruptThread = t
        t.start()

    def __interrupt(self, cb):
        if self.currentThread != None:
            self.currentThread.join()

        self.stop_thread = False
        cb()

    # ============ mid-level functions ===============

    def cleanOutHead(self, cb):
        # TODO: when this becomes a threaded method, need to change
        # all calls from within microscopeDriver class to call
        # private method (unthreaded, __cleanOutHead)
        """Cleans the current sample from the printer head,
        using a random ethanol well as cleaning solution

        :param cb: callback to reenable buttons on ui
        :type cb: function
        """
        t: Thread = Thread(target=self.__cleanOutHead, args=[cb])
        self.currentThread = t
        t.start()

    def __cleanOutHead(self, cb):
       # TODO: we don't know the cleaning process yet
        # might look something like:
        # blow current sample into waste container
        # suck in ethanol, blow out, suck int, blow out
        # then blow some air through the head for a while
        # raise NotImplementedError()

        # since this function is prevalent, I'm not gonna have
        # it raise an NotImplementedError (for testing purposes)

        # TODO: different behaviors for nothing vs something:
            # nothing should do an additional first step: suck in ethanol
        print("cleaning out the head")
        sleep(4)
        print("done cleaning out head")
        cb()

    def grabSample(self, wellID: str, cb):
        """
        Starts the thread to:
        Sucks the sample in wellID into the printer head

        :param wellID: The location of the sample on the plate
        :type wellID: str
        :param cb: callback function to re enable GUI buttons
        :type cb: function
        :raises ValueError: if wellID isn't formatted correctly or if
        """

        if not self.checkWellsValid([wellID]):
            cb()
            raise ValueError("well ID not valid")

        # TODO: uncomment if we want this feature
        # if not (wellID in self.sampleWells):
        #     cb()
        #     raise ValueError(f"{wellID} not in list of wells with sample")

        t = Thread(target=self.__grabSample, args=[wellID, cb])
        self.currentThread = t
        t.start()

    def __grabSample(self, wellID: str, cb):
        self.microscope.moveArmToUp()
        if self.__checkInterrupt(cb):return

        # additional logic to clean out the current sample if necessary
        def fakeCB(): x=3
        # TODO: if we're already holding sample from wellID should we still replace it?
        if self.microscope.currentSample != self.microscope.chip.CHAN_EMPTY:
            self.__cleanOutHead(fakeCB)

        if self.__checkInterrupt(cb):return

        self.microscope.movePrinterOverWell(wellID)
        if self.__checkInterrupt(cb):return

        self.microscope.movePrinterIntoWell()
        if self.__checkInterrupt(cb):return

        self.microscope.getSample(wellID)
        if self.__checkInterrupt(cb):return

        self.microscope.moveArmToUp()
        cb()

    def printCurrToK(self, num, cb):
        """Prints the currently held sample to num channels, starting from the first channel
        Assumes the printer head is already down. Does not move printer head back up
        :param cb: _description_
        :type cb: function
        """
        t:Thread = Thread(target=self.__printCurrToK, args=[num, cb])
        self.currentThread = t
        t.start()

    def __printCurrToK(self, num, cb):
        if self.__checkInterrupt(cb):return

        # self.microscope.moveArmToUp()
        # if self.__checkInterrupt(cb):return

        for i in range(1, num+1):
            self.microscope.moveToChannelNoLift(i)
            if self.__checkInterrupt(cb):return
            self.microscope.printSample(i, save=False)
            if self.__checkInterrupt(cb):return

        self.microscope.moveChannelToCamNoLift(1)
        cb()


    def printToMultipleChannels(self, wellID: str, channels: list[int], cb):
        """Starts a thread that gets a sample from wellID
        and prints it to each channel in the channels list,
        cleaning the sample out of the head when done

        :param channels: list of channels to print to, passed directly from GUI
        :type channels: list[str]
        :param wellID: ID of well to grab sample from
        :type wellID: string
        :param cb: callback function used to reenable buttons on UI
        :type cb: function
        :raise ValueErorr: if channels or wellID are not valid or if any of the channels
        are already occupied
        """

        # make sure the entered channels are formatted correctly
        if not self.checkChannelsValid(channels):
            cb()
            raise ValueError("one or more channel numbers are invalid")

        # convert channels from strings to integers
        channels: list[int] = [int(channelNum) for channelNum in channels]

        # check to see if one of the inputted channels is already occupied
        validChannels: bool = True
        for channel in channels:
            contents = self.microscope.chip.getChannelContent(channel)
            if contents != self.microscope.chip.CHAN_EMPTY:
                print(f"ERROR: channel {channel} already holds {contents}")
                validChannels = False

        if not validChannels:
            cb()
            raise ValueError("refusing to print to already occupied channels")

        # check to see if wellID is valid
        if not self.checkWellsValid([wellID]):
            cb()
            raise ValueError(f"{wellID} isn't a valid wellID")


        # check if wellID has some sample in it
        #TODO: uncomment if we want to keep this feature
        # if not wellID in self.sampleWells:
            # cb()
            # raise ValueError(f"{wellID} doesn't contain anything")

        # all checks good
        t: Thread = Thread(target=self.__printToMultipleChannels, args=[wellID, channels, cb])
        self.currentThread = t
        t.start()

    def __printToMultipleChannels(self, wellID: str, channels: list[int], cb):
        """
        sucks in wellID, prints to each channel in channels (without lifting between)
        then cleans out sample from printer head
        """
        if self.__checkInterrupt(cb): return

        self.microscope.moveArmToUp()
        if self.__checkInterrupt(cb): return
        # arm is now up, safe to move stage

        # so we can call __grabSample, but don't want to re-enable buttons
        def fakeCB(): x = 3
        # get the desired sample, cleaning out last one if necessary
        self.__grabSample(wellID, fakeCB)
        if self.__checkInterrupt(cb): return

        # move over initial channel
        self.microscope.movePrinterOverChannel(channels[0])
        if self.__checkInterrupt(cb): return

        # move down to initial channel
        self.microscope.movePrinterDownToChannel()
        if self.__checkInterrupt(cb): return

        # print to each specified channel
        for channel in channels:
            # move to the channel without lifting the head before or after
            self.microscope.moveToChannelNoLift(channel)
            if self.__checkInterrupt(cb):return

            # put a single drop in the channel
            self.microscope.printSample(channel)
            if self.__checkInterrupt(cb): return

        # move the arm up when done with all channels
        self.microscope.moveArmToUp()
        if self.__checkInterrupt(cb): return

        # now get rid of sample from wellID
        self.__cleanOutHead(fakeCB)
        cb()

    def printSamplesToK(self, wellIDs: list[str], k: int, cb):
        """
        Prints a single drop from each sample in wellIDs to
        k different channels.
        Checks if inputs are valid, as well as if there
        will be enough room to print everything

        :param wellIDs: _description_
        :type wellIDs: list[str]
        :param k: number of channels to print each
        :type k: int
        :raises ValueError: if wellIDs aren't formatted correctly
        or if there aren't enough channels left on the chip for printing
        """

        # NOTE: These checks also need to satisfy the checks of
        # printToMultipleChannels, since we call that function
        k = int(k)

        if k < 1:
            cb()
            raise ValueError("k must be greater than 0")

        # check valid inputs / enough space on chip
        if not self.checkWellsValid(wellIDs):
            cb()
            raise ValueError("wellIDs not valid")

        # TODO: uncomment if we want to keep this feature
        # # whether or not each wellID has some sample in it
        # wellIDsExist = True
        # for wellID in wellIDs:
        #     if wellID not in self.sampleWells: wellIDsExist = False

        # if not wellIDsExist:
        #     cb()
        #     raise ValueError("not all wellIDs have sample in them")

        if len(self.microscope.getEmptyChannels()) < len(wellIDs) * k:
            cb()
            raise ValueError("not enough open channels to print to")

        # There may be more checks I'm not thinking of

        t: Thread = Thread(target=self.__printSamplesToK, args=[wellIDs, k, cb])
        self.currentThread = t
        t.start()

    def __printSamplesToK(self, wellIDs: list[str], k: int, cb):
        def fakeCB(): x =  3
        # for each sample, print k times to a different empty channel
        emptyChannels: list[int] = self.microscope.getEmptyChannels()
        emptyIter = iter(emptyChannels)

        def fakeCB(): x = 3 # fake callback so we can call grabSample

        # for each wellID:
            # grab sample
            # for 0 ... k, print to one of the empty channels
            # clean out the head

            # the above lines describe self.__printToMultipleChannels
        for wellID in wellIDs:
            # parse out next k empty channels
            chans = [next(emptyIter) for _ in range(k)]
            if self.__checkInterrupt(cb): return

            # now we can call __printToMultipleChannels with those channels
            self.__printToMultipleChannels(wellID, chans, fakeCB)
            # the above checks for interrupts

        # now we're done. Clean out head once more for good measure
        self.__cleanOutHead(fakeCB)
        cb()

#  ============= Helper methods ===================

    def getStageXY(self) -> int:
        """
        Gets the XY position of the stage in number of steps
        """
        return self.microscope.getStageXY()

    def checkWellsValid(self, wells: list[str]):
        """
        returns true if each well is a unique and valid index on the
            current plate
        false if there are duplicates / wellIDs are not valid
        note: IDs must have an uppercase letter
        """

        if len(wells) == 0: return False

        try:
            for well in wells:
                if (len(well) not in (2, 3)):
                    return False
                row = str(well[0])
                if (row not in string.ascii_uppercase[0: self.microscope.plate.numRows]):
                    return False
                col = int(well[1:])
                if col not in range(1, self.microscope.plate.numCols + 1):
                    return False

        except ValueError:  # in case casting fails
            return False

        wellSet = list(dict.fromkeys(wells))
        if (len(wellSet) != len(wells)):
            # means there were some duplicates in original input
            return False
        return True

    def checkChannelsValid(self, channels: list[str]) -> bool:
        """
        returns true if each channel in the channels list is valid for
        the current chip

        :param channels: list of channels numbers as strings
        :type channels: list[str]
        :return: whether or not each channel is well formatted
        :rtype: bool
        """
        if len(channels) == 0: return False

        try:
            for channel in channels:
                if int(channel) < 1 or int(channel) > self.microscope.chip.numChan:
                    return False
        except ValueError:  # if casting to integer fails
            return False

        chanSet = list(dict.fromkeys(channels))
        if len(chanSet) != len(channels):
            return False

        return True

    def getChannelContents(self) -> list[str]:
        """returns a list of which sample is stored
        in each channel where list[i] is what is stored
        in channel i + 1. Channel numbers start from 1, not 0

        :return: a list of what is in each channel
        :rtype: list[str]
        """

        return self.microscope.getAllChannelContents()

    def __checkInterrupt(self, cb) -> bool:
        """
        Helper function to check if an interrupt command was issued
        If one was issued, this command will call cb and return true.
        Otherwise, returns false

        :param cb: callback function used to reenable buttons on UI
        :type cb: function
        :return: True if an interrupt was issued, False otherwise
        :rtype: bool
        """
        if self.stop_threads:  # interrupt issued
            cb()
            return True
        else:
            return False

    def close(self, cb):
        """
        Closes all connected devices.
        Issues an interrupt command, meaning all movement will be
        interrupted
        """
        print("driver closing")
        self.interrupt(cb)
        print("\tinterrupt command issued")
        # print(self.interruptThread)
        self.interruptThread.join()
        print("\tinterrupt thread joined")
        self.microscope.close()
        print("\tmicroscope closed")

