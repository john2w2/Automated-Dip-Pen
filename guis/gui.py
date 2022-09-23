from cgitb import text
from email import message
import tkinter as tk
import sys
sys.path.append("C:/Users/19199/Desktop/automated-sca/src")

from tkinter import Button, ttk
from tkinter import messagebox
from time import sleep
from threading import Thread
from microscopeDriver import MicroscopeDriver
from gui_widgets.camWidget import CamWidget
from gui_widgets.wellSelect import WellSelect

driver: MicroscopeDriver = None

DISABLE_BUTTONS = []  # list of buttons that should be disabled for movement commands
STARTUP_DISABLED_BUTTONS = [] # list of buttons that should be disabled before startup, enabled once startup succeeds
CALIB_DICT = {} # dictionary mapping device name to calibration status
ARM_ENABLES = [] # buttons that get enabled by the arm being calibrated

WELL_PLATE_SIZE = None

CALIBRATED = "calibrated"
NOT_CALIBRATED = "not calibrated"
LOADED = "loaded from previous run"

interruptBtn: ttk.Button = None # global reference to interrupt button
moveToSafeBtn: ttk.Button = None # global reference to move to safe button
# driver: MicroscopeDriver = None # global reference to driver


root = tk.Tk()
# root = ThemedTk(theme='yaru')
root.title("Automated Single Cell Printing")

# sv_ttk.set_theme("dark")  # Set light theme

s=ttk.Style()

# s.theme_use('clam')

# helper method used to add elements with grid more easily
def grid(widget, row, col, padx, pady, sticky='nsew'):
    widget.grid(row=row,column=col, padx=padx, pady=pady, sticky=sticky)

class HighLevel(ttk.LabelFrame):
    def __init__(self, parent):
        ttk.LabelFrame.__init__(self, parent, text="High Level")
        for i in range(6): self.rowconfigure(i, weight=1)
        self.columnconfigure(0, weight=1)

        self.startupOpen = False

        startupButton = ttk.Button(self, text="open startup menu", command=self.openStartup)
        grid(startupButton, 0, 0, 5, 5)

        global interruptBtn
        interruptBtn = ttk.Button(self, text="INTERRUPT", command=self.interrupt)
        grid(interruptBtn, 1, 0, 5, 5)
        interruptBtn["state"] = "disabled"

        global moveToSafeBtn
        moveToSafeBtn = ttk.Button(self, text="move arm to safe position", command=self.moveToSafe)
        grid(moveToSafeBtn, 2, 0, 5, 5, sticky='ew')
        moveToSafeBtn["state"] = "disabled"

        self.singleToMultiple = SingleToMultiple(self)
        grid(self.singleToMultiple, 3, 0, 5, 5, sticky='ew')

        self.toK = PrintEachToK(self)
        grid(self.toK, 4, 0, 5, 5, sticky='ew')

    def openStartup(self):
        def on_closing():
            self.startupMenu.destroy()
            self.startupOpen = False

        if not self.startupOpen:
            self.startupMenu = tk.Toplevel(root)
            self.startupMenu.title("Startup Menu")

            # TODO: widget goes here
            grid(self.StartupMenu(self.startupMenu), 0,0,0,0)

            self.startupMenu.protocol("WM_DELETE_WINDOW", on_closing)
            self.startupOpen = True
        else:
            self.startupMenu.focus()

    def interrupt(self):
        """ sends an interrupt command to the microscope driver"""
        # TODO: call driver interrupt here
        def cb():
            moveToSafeBtn["state"] = "normal"

        driver.interrupt(cb)

    def moveToSafe(self):
        moveToSafeBtn["state"] = "disabled"
        driver.resetToSafeState()

    class StartupMenu(ttk.Frame):
        # TODO: make this a pop-out window
        def __init__(self, parent):
            ttk.LabelFrame.__init__(self, parent)
            for i in range(3):
                self.rowconfigure(i, weight=1)
                self.columnconfigure(i, weight=1)

            portFrame = ttk.LabelFrame(self, text="COM ports")
            self.priorLab = ttk.Label(portFrame, text="Prior port")
            grid(self.priorLab, 0,0,0,0)
            self.priorEnt = ttk.Entry(portFrame)
            self.priorEnt.insert(0, "COM6")
            grid(self.priorEnt, 0,1,0,0)
            self.ardLab = ttk.Label(portFrame, text="Arduino port")
            grid(self.ardLab, 1,0,0,0)
            self.ardEnt = ttk.Entry(portFrame)
            self.ardEnt.insert(0, "COM7")
            grid(self.ardEnt, 1,1,0,0)
            grid(portFrame, 0,0,5,5)

            plateFrame = ttk.LabelFrame(self, text="Plate")
            self.wellSize = tk.StringVar()
            dd = ttk.OptionMenu(plateFrame, self.wellSize, "96 wells", "6 wells" , "96 wells", "384 wells")
            dd.pack(expand=True, fill="both")
            grid(plateFrame, 1, 0, 5, 5)

            chipFrame = ttk.LabelFrame(self, text="Chip Parameters")

            numChanLab = ttk.Label(chipFrame, text="Number of channels")
            self.numChanEnt = ttk.Entry(chipFrame)
            self.numChanEnt.insert(0, "40")

            grid(numChanLab, 0, 0, 5, 5)
            grid(self.numChanEnt, 0, 1, 5, 5)

            chanDistLab = ttk.Label(chipFrame, text="Distance between centers \n of adjacent channels (um)")
            self.chanDistEnt = ttk.Entry(chipFrame)
            self.chanDistEnt.insert(0, "260")

            grid(chanDistLab, 1, 0, 5, 5)
            grid(self.chanDistEnt, 1, 1, 5, 5)

            grid(chipFrame, 2, 0, 5, 5)

            startupBtn = ttk.Button(self, text="start up the device", command=self.startUp)
            startupBtn.grid(row=3, column=0, columnspan=2, stick='nsew')
            self.items = [self.priorLab, self.priorEnt, self.ardLab, self.ardEnt, startupBtn, dd, 
                            numChanLab, self.numChanEnt, chanDistLab, self.chanDistEnt]

            # if driver is already connected, we don't want to allow them to try to connect again
            if driver != None:
                for item in self.items: item["state"] = "disabled"

        def startUp(self):
            """ loads in the device using the specified parameters """
            # COM ports will raise errors so no need to check
            priorP = self.priorEnt.get()
            ardP = self.ardEnt.get()
            plateSize = self.wellSize.get()  # turn this from "x wells" to x:int
            numChan = self.numChanEnt.get()  # cast to int, check > 0
            chanDist = self.chanDistEnt.get() # cast to int, check > 0
            try:
                plateSize = int(self.wellSize.get().split(" wells")[0])  # turn this from "x wells" to x:int
                numChan = int(self.numChanEnt.get())  # cast to int, check > 0
                chanDist = int(self.chanDistEnt.get()) # cast to int, check > 0
                if numChan < 0 or chanDist < 0: raise ValueError()
            except:
                messagebox.showerror(title="Bad Parameters", message="please make sure your parameters are valid")
                return # exit method, don't start up the device

            try:
                def cb():
                    for item in STARTUP_DISABLED_BUTTONS: item["state"] = "normal"
                    for item in self.items: item["state"] = "disabled" 
                
                # set plate size for well select widget
                global WELL_PLATE_SIZE
                WELL_PLATE_SIZE = plateSize

                global driver
                driver = MicroscopeDriver(priorPort=priorP, arduinoPort=ardP,
                                          plateSize=plateSize, numChan=numChan, 
                                          chanDist=chanDist, cb=cb)

            except ConnectionError as e:
                # some popup window saying something went wrong
                messagebox.showerror(title="connection error", message="either COM ports are incorrect or devices are accessed by another resource")

class SingleToMultiple(ttk.LabelFrame):
    def __init__(self, parent):
        ttk.Labelframe.__init__(self, parent, text="Print single sample to multiple channels")

        for i in range(4): self.rowconfigure(i, weight=1)
        self.columnconfigure(0, weight=1)

        s2mEntLabel = ttk.Label(self, text="choose sample", anchor="center")
        grid(s2mEntLabel, 0, 0, 0, 5, sticky='ew')

        self.s2mWellEntry = ttk.Entry(self)
        grid(self.s2mWellEntry, 1, 0, 0, 5, sticky='ew')


        s2mChanEntLabel = ttk.Label(self, text="list of channels", anchor="center")
        grid(s2mChanEntLabel, 2, 0, 0, 5, sticky='ew')

        self.s2mChanEntry = ttk.Entry(self)
        self.s2mChanEntry["state"] = "disabled"
        grid(self.s2mChanEntry, 3, 0, 0, 5, sticky='ew')

        goBtn = ttk.Button(self, text="start")
        grid(goBtn, 4, 0, 0,0)

        for child in self.winfo_children(): ARM_ENABLES.append(child)

    def printSingleToMultiple(self):
        sample = self.s2mWellEntry.get()
        channels = self.s2mChanEntry.get()
        def cb():
            interruptBtn["state"] = "disabled"
            for btn in STARTUP_DISABLED_BUTTONS: btn["state"] = "normal"

        try:
            for btn in STARTUP_DISABLED_BUTTONS: btn["state"] = "disabled"
            interruptBtn["state"] = "normal"
            driver.printToMultipleChannels(sample, channels, cb)

        except Exception as e:
            messagebox.showerror(title="error", message=str(e))
class PrintEachToK(ttk.Labelframe):
    def __init__(self, parent):
        ttk.LabelFrame.__init__(self, parent, text="Print Samples to K")
        for i in range(4): self.rowconfigure(i, weight=1)
        self.columnconfigure(0, weight=1)

        self.wellEnt = []

        self.wellSelectOpen = False

        self.openWellsBtn = ttk.Button(self, text="open well select menu", cursor="hand2", command=self.openWellSelectMenu)
        grid(self.openWellsBtn, 0, 0, 5, 5)

        self.selectedWellsList = ttk.Label(self, text="selected wells:", font=("Roboto Mono","10"))
        grid(self.selectedWellsList, 1, 0, 5, 5)

        kLabel = ttk.Label(self, text="number of channels for each sample")
        grid(kLabel, 2, 0, 5, 5)

        self.kEnt = ttk.Entry(self)
        grid(self.kEnt, 3, 0, 5, 5)

        goBtn = ttk.Button(self, text="start")
        grid(goBtn, 4, 0, 0,0)

        for child in self.winfo_children(): ARM_ENABLES.append(child)

    #TODO: function to call printing, handling bad input
    #TODO: some way to get selected from welLSelect (some array stored in PrintEachToK, pass to wellselect)

    def openWellSelectMenu(self):
        def on_closing():
                self.wellSelectMenu.destroy()
                self.wellSelectOpen = False

        if not self.wellSelectOpen:
            self.wellSelectMenu = tk.Toplevel(root)
            self.wellSelectMenu.title("Well Select Menu")
            # NOTE: WellSelect is an imported class
            self.selectWidget = WellSelect(self.wellSelectMenu, plateSize=WELL_PLATE_SIZE)
            grid(self.selectWidget, 0,0,0,0)
            self.selectWidget.grid(row=0, column=0, columnspan=2, padx=5, pady=5, sticky='nsew')

            saveBtn = ttk.Button(self.wellSelectMenu, text="save wells", command=self.saveWells)
            grid(saveBtn, 1, 0, 5, 5)

            cancelBtn = ttk.Button(self.wellSelectMenu, text="cancel", command=on_closing)
            grid(cancelBtn, 1, 1, 5, 5)
            
            self.wellSelectMenu.protocol("WM_DELETE_WINDOW", on_closing)
            self.wellSelectOpen = True

    def saveWells(self):
        selected = self.selectWidget.getSelected()
        self.wellEnt = selected
        enIter = iter(self.wellEnt)
        wrapped = ""
        for i in range(len(self.wellEnt)):
            if i % 10 == 9: wrapped += '\n'
            wrapped += next(enIter) + ' '
        self.selectedWellsList.config(text=f"selected wells: {wrapped}")

    def printToK(self):
        # TODO: implement this
        # get well entries
        pass

class CalibrationFrame(ttk.LabelFrame):
    def __init__(self, parent):
        ttk.LabelFrame.__init__(self, parent, text="Calibration and Sanity checks")
        for i in range(4): self.rowconfigure(i, weight=1)
        self.columnconfigure(0, weight=1)

        self.calibOpen = False
        self.sanityOpen = False

        openCalibMenu = ttk.Button(self, text="open calibration menu", command=self.openCalibMenu)
        STARTUP_DISABLED_BUTTONS.append(openCalibMenu)
        grid(openCalibMenu, 0, 0, 5, 5)

        openSanity = ttk.Button(self, text="open sanity check menu", command=self.openSanityMenu)
        ARM_ENABLES.append(openSanity)
        grid(openSanity, 1, 0, 5, 5)

        self.calibList = CalibratedList(self, CALIB_DICT)
        grid(self.calibList, 2, 0, 5, 5)

        # STARTUP_DISABLED_BUTTONS


    def openCalibMenu(self):
        def on_closing():
            self.calibMenu.destroy()
            self.calibOpen = False
            for item in STARTUP_DISABLED_BUTTONS: item["state"] = "normal"

        if not self.calibOpen:
            for item in STARTUP_DISABLED_BUTTONS: item["state"] = "disabled"
            self.calibMenu = tk.Toplevel(root)
            self.calibMenu.title("Calibration Menu")
            self.calibMenu.rowconfigure(0, weight=1)
            self.calibMenu.columnconfigure(0, weight=1)
            grid(CalibrationMenu(self.calibMenu), 0,0,10,10)
            self.calibMenu.protocol("WM_DELETE_WINDOW", on_closing)
            self.calibOpen = True
        else:
            self.calibMenu.focus()

    def openSanityMenu(self):
        def on_closing():
            for item in STARTUP_DISABLED_BUTTONS: item["state"] = "normal"
            sanityMenu.destroy()
            self.sanityOpen = False

        if not self.sanityOpen:
            for item in STARTUP_DISABLED_BUTTONS: item["state"] = "disabled"
            sanityMenu = tk.Toplevel(root)
            sanityMenu.title("Sanity Check Menu")
            sanityMenu.rowconfigure(0, weight=1)
            sanityMenu.columnconfigure(0, weight=1)
            grid(SanityMenu(sanityMenu), 0, 0, 0, 0)
            sanityMenu.protocol("WM_DELETE_WINDOW", on_closing)
            self.sanityOpen = True

class CalibrationMenu(ttk.Frame):
    def __init__(self, parent):
        ttk.Frame.__init__(self, parent)
        for i in range(10): self.rowconfigure(i, weight=1)
        self.columnconfigure(0, weight=1)
        self.columnconfigure(1, weight=1)
        self.buttons = []

        #TODO: figure out how to make calib button not obscenely large
        # TODO: allow user to input all 3 stage positions (measured in mm from bottom of limit switch)
        self.calibArmBtn = ttk.Button(self, text="calibrate arm Z axis\n(move to top limit switch)", command=self.calibArm)
        self.calibArmBtn.grid(row=0, column=0, rowspan=1, sticky='nsew', padx=5, pady=5)
        self.buttons.append(self.calibArmBtn)

        stageCal = self.StageCalibration(self, self.buttons)
        stageCal.grid(row=1, column=0, rowspan=1,padx=5, pady=5, sticky='nsew')

        printDrop = self.PrintDropTest(self, self.buttons)
        printDrop.grid(row=0, column=1, rowspan=3, padx=5, pady=5, sticky='nsew')

        getSample = self.ManualGetSample(self, self.buttons)
        getSample.grid(row=3, column=0, rowspan=1, sticky='nsew', padx=5, pady=5)
  
        pressureCal = self.PressureCalibration(self, self.buttons)
        pressureCal.grid(row=2, column=0, rowspan=1, sticky='nsew', padx=5, pady=5)

        armPos = self.ArmPositions(self, self.buttons)
        armPos.grid(row=3, column=1, sticky='nsew')

        for item in self.buttons: item["state"] = "disabled" if CALIB_DICT["arm"].cget('text') != f"arm: {CALIBRATED}" else "normal"
        self.calibArmBtn["state"] = "normal"


    def calibArm(self):
        """ recalibrates the z axis arm """

        for btn in self.buttons: btn["state"] = "disabled"
        self.calibArmBtn["state"] = "disabled"
        # can't interrupt this movement unfortunately

        def cb():
            for btn in self.buttons: btn["state"] = "normal"
            CALIB_DICT["arm"].config(text=f"arm: {CALIBRATED}", background="#65d92b")
            self.buttons.append(self.calibArmBtn)
            STARTUP_DISABLED_BUTTONS.extend(ARM_ENABLES)
            for item in self.buttons: item["state"] = "normal"
        
        driver.calibrateZArm(cb)

    class ArmPositions(ttk.LabelFrame):
        def __init__(self, parent, calibButtons):
            # TODO: somehow need to load these from a file to fill entries
            # or a button that pops up a window that will list them out
            ttk.LabelFrame.__init__(self, parent, text="Save arm Positions (mm)")
            description = ttk.Label(self, text=" Positions of arm, measured in mm from the top of the \n motor mount to the top limit switch's lever")
            description.grid(row=0, column=0, columnspan=3, sticky='nsew')

            self.calibButtons = calibButtons

            # grid(description, 0, 0, 5, 5)
            # TODO: should this also allow you to move the arm around??????????
            self.upEnt = ttk.Entry(self)
            saveUpBtn = ttk.Button(self, text="save 'safe' position", command=self.saveSafe)
            grid(self.upEnt, 1, 0, 5, 5)
            grid(saveUpBtn, 1, 1, 5, 5)

            self.chipEnt = ttk.Entry(self)
            saveChipBtn = ttk.Button(self, text="save 'above chip' position", command=self.saveChip)
            grid(self.chipEnt, 2, 0, 5, 5)
            grid(saveChipBtn, 2, 1, 5, 5)

            self.wellEnt = ttk.Entry(self)
            saveWellBtn = ttk.Button(self, text="save 'in well' position", command=self.saveWell)
            grid(self.wellEnt, 3, 0, 5, 5)
            grid(saveWellBtn, 3, 1, 5, 5)

            moveMMFrame = ttk.LabelFrame(self, text="move to absolute position (mm)")
            # entry. go button
            self.mmEnt = ttk.Entry(moveMMFrame)
            self.mmEnt.insert(0, "0")
            grid(self.mmEnt, 0, 0, 0, 0)
            goMMBtn = ttk.Button(moveMMFrame, text="move to absolute position (mm)", command=self.moveToMM)
            grid(goMMBtn, 0, 1, 0, 0)
            moveMMFrame.grid(row=4, column=0, columnspan=2, sticky='nsew')

            showSavedBtn = ttk.Button(self, text="show saved positions", command=self.showSavedPositions)
            showSavedBtn.grid(row=5, column=0, columnspan=2, sticky='nsew')

            showCurrentBtn = ttk.Button(self, text="show current position of arm", command=self.showCurrentPosition)
            showCurrentBtn.grid(row=6, column=0, columnspan=2, sticky='nsew')

            # TODO: these buttons don't actually do anything right now, need to implement them later

            calibButtons.extend([self.upEnt, saveUpBtn, self.chipEnt, saveChipBtn, self.wellEnt, saveWellBtn, self.mmEnt, goMMBtn, showSavedBtn, showCurrentBtn])

        def saveSafe(self):
            pos = self.upEnt.get()
            try:
                pos = float(pos)
                driver.saveSafeZPosition(pos)
            except Exception as e:
                messagebox.showerror(title="Error saving value", message=str(e))

        def saveChip(self):
            pos = self.chipEnt.get()
            try:
                pos = float(pos)
                driver.saveChipZPosition(pos)
            except Exception as e:
                messagebox.showerror(title="Error saving value", message=str(e))
        
        def saveWell(self):
            pos = self.wellEnt.get()
            try:
                pos = float(pos)
                driver.saveWellZPosition(pos)
            except Exception as e:
                messagebox.showerror(title="Error saving value", message=str(e))
            
        def moveToMM(self):
            pos = self.mmEnt.get()

            def cb():
                # TODO
                interruptBtn["state"] = "disabled"
                for itm in self.calibButtons: itm["state"] = "normal"
            try:
                
                pos = float(pos)

                interruptBtn["state"] = "normal"
                for itm in self.calibButtons: itm["state"] = "disabled"
                driver.moveToZAbsoluteInUM(pos * 1000, cb)
            except Exception as e:
                messagebox.showerror(title="Error", message=str(e))

        def showSavedPositions(self):
            upPos = (driver.microscope.arm.zUpPos * driver.microscope.arm.zmotor.stepper.distPerStep) / 1000
            chipPos = (driver.microscope.arm.zChannelPos * driver.microscope.arm.zmotor.stepper.distPerStep) / 1000
            wellPos = (driver.microscope.arm.zWellPos * driver.microscope.arm.zmotor.stepper.distPerStep) / 1000

            messagebox.showinfo(title="Saved Positions", message=f"safe: {upPos}mm \nabove chip: {chipPos}mm \nin well: {wellPos}mm")

        def showCurrentPosition(self):
            pos = driver.microscope.arm.zmotor.getZPosInUM() / 1000
            messagebox.showinfo(title="Current Motor Position", message=f"{pos}")

    class StageCalibration(ttk.LabelFrame):
        def __init__(self, parent, calibButtons):
            ttk.Labelframe.__init__(self, parent, text="Stage Calibration")
            # self.calibStageFrame = ttk.Labelframe(self, text="Positioning")

            # resetStageLab = ttk.Label(self.calibStageFrame, text="move stage until it hits the bottom and right limit \n switches, then hit \n \"recalibrate stage positioning\"")
            # grid(resetStageLab, 0, 0, 5, 5)
            # self.resetStageBtn = ttk.Button(self.calibStageFrame, text="recalibrate stage positioning", command=self.resetStagePositioning)
            # grid(self.resetStageBtn, 1,0,5,5)

            # grid(self.calibStageFrame, 0, 0, 5, 5)

            self.firstChanBtn = ttk.Button(self, text="save current position as 'first channel on camera'", command=self.saveFirstChannelCamPos)
            grid(self.firstChanBtn, 1, 0, 5, 5)

            self.firstWellBtn = ttk.Button(self, text="save current position as 'first well centered on camera'", command=self.saveFirstWellCamPos)
            grid(self.firstWellBtn, 2,0,5,5)
            calibButtons.extend([self.firstChanBtn, self.firstWellBtn])
            # calibButtons.extend([self.resetStageBtn, self.firstChanBtn, self.firstWellBtn])

        def resetStagePositioning(self):
            driver.calibrateStage()
            CALIB_DICT["stage"].config(text=f"stage: {CALIBRATED}", background="#65d92b")

        def saveFirstChannelCamPos(self):
            driver.saveFirstChannelCamPos()
            CALIB_DICT["first channel"].config(text=f"first channel: {CALIBRATED}", background="#65d92b")

        def saveFirstWellCamPos(self):
            # TODO: this will eventually be a threaded function that needs to disable buttons
            # (when automation integrated)
            driver.saveFirstWellCamPos()
            CALIB_DICT["first well"].config(text=f"first well: {CALIBRATED}", background="#65d92b")

    class PressureCalibration(ttk.LabelFrame):
        def __init__(self, parent, calibButtons):
            ttk.LabelFrame.__init__(self, parent, text="Pressure Calibration")
            self.calibButtons = calibButtons
            # recalibrate OB1
            self.calOB1 = ttk.Button(self, text="recalibrate OB1 (make sure it's capped)", command=self.calibOB1)
            # save the 3 pressure values
            grid(self.calOB1, 0, 0, 5, 5)
            self.pressureFrame = ttk.LabelFrame(self, text="Specify Pressure Values")

            inPLab = ttk.Label(self.pressureFrame, text="In pressure")
            self.inPEnt = ttk.Entry(self.pressureFrame)
            self.inPEnt.insert(0, "-80.0")
            grid(inPLab, 0, 0, 5, 0)
            grid(self.inPEnt, 0, 1, 5, 0)

            inPDurLab = ttk.Label(self.pressureFrame, text="# of seconds to apply\nin pressure for")
            self.inPSecEnt = ttk.Entry(self.pressureFrame)
            self.inPSecEnt.insert(0, "3") # should match default value in pressure.py
            grid(inPDurLab, 1, 0, 5, 5)
            grid(self.inPSecEnt, 1, 1, 5, 0)

            eqPLab = ttk.Label(self.pressureFrame, text="Equilibrium pressure")
            self.eqPEnt = ttk.Entry(self.pressureFrame)
            self.eqPEnt.insert(0, "0")
            grid(eqPLab, 2, 0, 5, 0)
            grid(self.eqPEnt, 2, 1, 5, 0)

            outPLab = ttk.Label(self.pressureFrame, text="Out pressure")
            self.outPEnt = ttk.Entry(self.pressureFrame)
            self.outPEnt.insert(0, "80.0")
            grid(outPLab, 3, 0, 5, 0)
            grid(self.outPEnt, 3, 1, 5, 0)

            outPDurLab = ttk.Label(self.pressureFrame, text="# of seconds to apply\nout pressure for")
            self.outPSecEnt = ttk.Entry(self.pressureFrame)
            self.outPSecEnt.insert(0, "3") # has to match default value in pressure.py
            grid(outPDurLab, 4, 0, 5, 5)
            grid(self.outPSecEnt, 4, 1, 5, 0)

            saveVals = ttk.Button(self.pressureFrame, text="Save pressure values", command=self.savePressures)
            saveVals.grid(row=5, column=0, columnspan=2, padx=5, pady=5, sticky='nsew')

            grid(self.pressureFrame, 1, 0, 5, 5)

            calibButtons.extend([self.calOB1, self.inPEnt, self.eqPEnt, self.outPEnt, saveVals, self.outPSecEnt, self.inPSecEnt])

        def calibOB1(self):
            res = messagebox.askokcancel(title="recalibrate OB1", message="Are you sure you want to recalibrate the OB1? This takes about 3 minutes. Also, please don't run any other functions while calibration is happening")
            if res:
                driver.recalibrateOB1()

        def savePressures(self):
            # check if inputs are valid
            inP = self.inPEnt.get()
            eqP = self.eqPEnt.get()
            outP = self.outPEnt.get()
            inPS = self.inPSecEnt.get()
            outPS = self.outPSecEnt.get()
            try:
                inP = float(inP)
                eqP = float(eqP)
                outP = float(outP)
                inPS = float(inPS)
                outPS = float(outPS)
                if (outPS < 0 or inPS < 0): messagebox.showerror(title="bad time input", message="Please use a positive number for time") 
                
                driver.savePressures(inPressure=inP, eqPressure=eqP, outPressure=outP)
                driver.microscope.printer.pressure.calibDurations(inPTime=inPS, outPTime=outPS) # TODO: add more functions to lower level classes if you want

                CALIB_DICT["pressures"].config(text=f"pressures: {CALIBRATED}", background="#65d92b")

            except ValueError:
                messagebox.showwarning(title="bad pressure input", message="please check your values")

    class ManualGetSample(ttk.LabelFrame):
        def __init__(self, parent, calibButtons):
            ttk.LabelFrame.__init__(self, parent, text="Manually Get a Sample")
            for i in range(5): self.rowconfigure(i, weight=1)
            self.columnconfigure(0, weight=1)

            self.calibButtons = calibButtons

            self.instructions = ttk.Label(self, text="Please fill a well on a 6-well plate, then click start to begin")
            grid(self.instructions, 0,0,5,0)

            self.startBtn = ttk.Button(self, text="start", command=self.start)
            grid(self.startBtn, 1, 0, 5, 0)

            self.moveOverWellBtn = ttk.Button(self, text="moved over well", command=self.movedOverWell)
            grid(self.moveOverWellBtn, 2, 0, 5, 0)
            self.moveOverWellBtn["state"] = "disabled"

            self.intoWellBtn = ttk.Button(self, text="move down into well", command=self.moveIntoWell)
            grid(self.intoWellBtn, 3, 0, 5, 0)
            self.intoWellBtn["state"] = "disabled"

            self.getSampleBtn = ttk.Button(self, text="get sample", command=self.getSample)
            grid(self.getSampleBtn, 4, 0, 5, 0)
            self.getSampleBtn["state"] = "disabled"

            self.moveUpBtn = ttk.Button(self, text="move arm back up", command=self.moveUp)
            grid(self.moveUpBtn, 5, 0, 5, 0)
            self.moveUpBtn["state"] = "disabled"

            self.abortBtn = ttk.Button(self, text="abort", command=self.abort)
            grid(self.abortBtn, 6, 0, 5, 0)
            self.abortBtn["state"] = "disabled"

            calibButtons.append(self.startBtn)

        def start(self):
            self.startBtn["state"] = "disabled"
            self.abortBtn["state"] = "normal"
            for item in self.calibButtons: item["state"] = "disabled"
            interruptBtn["state"] = "normal"
            # moveToSafeBtn["state"] = "disabled"

            def cb():
                self.moveOverWellBtn["state"] = "normal"
                self.instructions.configure(text="Move printer head above a well containing solution")
                interruptBtn["state"] = "disabled"
                # moveToSafeBtn["state"] = "normal"

            driver.moveArmToUp(cb)
            
        def movedOverWell(self):
            self.moveOverWellBtn["state"] = "disabled"
            self.intoWellBtn["state"] = "normal"
            self.instructions.configure(text="press 'move into well'")

        def moveIntoWell(self):
            self.intoWellBtn["state"] = "disabled"
            interruptBtn["state"] = "normal"
            # moveToSafeBtn["state"] = "disabled"
            #cb
            def cb():
                self.getSampleBtn["state"] = "normal"
                print("sample button normal")
                self.instructions.configure(text="press 'get sample'")
                interruptBtn["state"] = "disabled"
                # moveToSafeBtn["state"] = "normal"

            driver.movePrinterIntoWell(cb)  

        def getSample(self):
            self.getSampleBtn["state"] = "disabled"
            # moveToSafeBtn["state"] = "disabled"
            def cb():
                self.moveUpBtn["state"] = "normal"
                self.instructions.configure(text="press 'move arm up'")
                # moveToSafeBtn["state"] = "normal"

            driver.grabSampleNoMove(cb)

        def moveUp(self):
            self.moveUpBtn["state"] = "disabled"
            interruptBtn["state"] = "normal"
            # moveToSafeBtn["state"] = "disabled"
            def cb():
                self.instructions.configure(text="There should now be a sample in the printer head.\nPress start to redo")
                self.abortBtn["state"] = "disabled"
                self.startBtn["state"] = "normal"
                for item in self.calibButtons: item["state"] = "normal"
                interruptBtn["state"] = "disabled"
                # moveToSafeBtn["state"] = "normal"

            driver.moveArmToUp(cb)

        def abort(self):
            self.startBtn["state"] = "normal"
            def cb():
                self.instructions.config(text="Aborted. Press start to recalibrate")
                self.moveOverWellBtn["state"] = "disabled"
                self.intoWellBtn["state"] = "disabled"
                self.getSampleBtn["state"] = "disabled"
                self.moveUpBtn["state"] = "disabled"
                self.abortBtn["state"] = "disabled"
                for item in self.calibButtons: item["state"] = "normal"

            driver.interrupt(cb)

    class PrintDropTest(ttk.LabelFrame):
        def __init__(self, parent, calibButtons):
            ttk.LabelFrame.__init__(self, parent, text="Test Printing Drops")
            self.columnconfigure(0, weight=1)
            self.calibButtons = calibButtons

            # TODO: fill in instructions
            self.instructions = ttk.Label(self, text="TBD, just a static description of each button")
            grid(self.instructions, 0, 0, 5, 0)

            self.startBtn = ttk.Button(self, text="start", command=self.start)
            grid(self.startBtn, 1, 0, 5, 0)

            self.toChipBtn = ttk.Button(self, text="move arm down to chip\n(make sure arm is above chip before)", command=self.toChip)
            grid(self.toChipBtn, 2, 0, 5, 0)
            self.toChipBtn["state"] = "disabled"

            # TODO: this should be its own frame (maybe)
            self.pressureFrame = ttk.LabelFrame(self, text="edit and set equilibrium pressure")
            for i in range(2): self.pressureFrame.columnconfigure(i, weight=1)
            self.eqPEnt = ttk.Entry(self.pressureFrame)
            grid(self.eqPEnt, 0, 0, 0, 0)
            self.eqPEnt["state"] = "disabled"
            self.eqPBtn = ttk.Button(self.pressureFrame, text="update", command=self.saveSetEqP) # save pressure value, then set to eqp pressure
            # NOTE: should probably limit eq pressure here between -20.0 to 20.0
            grid(self.eqPBtn, 0, 1, 0, 0)
            self.eqPBtn["state"] = "disabled"

            grid(self.pressureFrame, 3, 0, 5, 5)

            self.printBtn = ttk.Button(self, text="trigger print", command=self.togglePrint)
            grid(self.printBtn, 4, 0, 5, 0)
            self.printBtn["state"] = "disabled"

            self.gotoBtn = ttk.Button(self, text="show drop on cam", command=self.goto) # move arm up first # TODO: make a function in driver that moves up, then moves stage relatively by the negation of the offset
            grid(self.gotoBtn, 5, 0, 5, 0)
            self.gotoBtn["state"] = "disabled"

            self.setPntBtn = ttk.Button(self, text="save offset (line up drop on cam)", command=self.setPnt)
            grid(self.setPntBtn, 6, 0, 5, 0)
            self.setPntBtn["state"] = "disabled"

            self.upBtn = ttk.Button(self, text="move arm up", command=self.armUp)
            grid(self.upBtn, 7, 0, 5, 0)
            self.upBtn["state"] = "disabled"

            self.abortBtn = ttk.Button(self, text="abort process", command=self.abort) # stops arm movement
            # only enables done button, which will have an implicit moveArmUp command called
            grid(self.abortBtn, 8, 0, 5, 0)
            self.abortBtn["state"] = "disabled"

            self.doneBtn = ttk.Button(self, text="done", command=self.done) 
            grid(self.doneBtn, 9, 0, 5, 0) 
            self.doneBtn["state"] = "disabled"

            calibButtons.append(self.startBtn)
            self.printLoc = (None, None)
            self.offset = (None, None)

            # some fake(?) offset values

        def start(self):
            # TODO: should abort only be clickable during arm moves?
            # TODO: if I add a button to save the offset, then I don't need the entire drop offset menu
            #       since drop offset will also need move up / down
            self.abortBtn["state"] = "normal"
            self.toChipBtn["state"] = "normal"
            self.doneBtn["state"] = "normal"
            for btn in self.calibButtons: btn["state"] = "disabled"

        def toChip(self):
            self.toChipBtn["state"] = "disabled"
            interruptBtn["state"] = "normal"
            # moveToSafeBtn["state"] = "disabled"
            # cb
            def cb():
                self.upBtn["state"] = "normal"
                self.printBtn["state"] = "normal"
                self.eqPEnt["state"] = "normal"
                self.eqPBtn["state"] = "normal"
                interruptBtn["state"] = "disabled"
                # moveToSafeBtn["state"] = "normal"

            driver.movePrinterToChip(cb)

        def saveSetEqP(self):
            # also perform checks on save pressure here
            # TODO: new function in Pressure.py that lets you adjust equilibrium pressure rather than all three at once
            # should call set pressure after saving the new pressure
            pVal = self.eqPEnt.get()
            try:
                pVal = float(pVal)
                if pVal < -20.0 or pVal > 20.0:
                    # TODO: have a confirm button
                    res:bool = messagebox.askokcancel(title="abnormal equilibrium pressure", message=f'You entered {pVal} for your equilibrium pressure, which is outside of the range [-20.0, 20.0]. High equilibrium pressures may cause unwanted behavior. Are you sure you want to use this value?')
                    if not res: return
                
                # TODO: here is where we set equilibrium pressure, need to implement first
                driver.microscope.printer.pressure.saveAndSetEq(pVal)

            except ValueError:
                res = messagebox.showerror(title="bad input", message="Please be sure you entered a valid pressure value")

        def togglePrint(self):
            # disable everything, print a drop, re-enable
            # also save where we printed ( for offset calculation )
            self.upBtn["state"] = "disabled"
            self.eqPEnt["state"] = "disabled"
            self.eqPBtn["state"] = "disabled"
            self.doneBtn["state"] = "disabled"
            self.setPntBtn["state"] = "disabled"
            self.gotoBtn["state"] = "disabled"
            self.abortBtn["state"] = "disabled"

            self.printLoc = driver.getStageXY()

            def cb():
                self.upBtn["state"] = "normal"
                self.eqPEnt["state"] = "normal"
                self.eqPBtn["state"] = "normal"
                self.doneBtn["state"] = "normal"
                self.abortBtn["state"] = "normal"
                if self.printLoc != (None, None): self.setPntBtn["state"] = "normal"
                # if self.offset != (None, None): self.gotoBtn["state"] = "normal"
                self.gotoBtn["state"] = "normal" # just use previously loaded offset

            driver.printDropNoMove(cb)

        def goto(self):
            self.upBtn["state"] = "disabled"
            self.eqPEnt["state"] = "disabled"
            self.eqPBtn["state"] = "disabled"
            self.doneBtn["state"] = "disabled"
            self.setPntBtn["state"] = "disabled"
            self.gotoBtn["state"] = "disabled"
            self.abortBtn["state"] = "disabled"
            self.printBtn["state"] = "disabled"


            def cb():
                self.gotoBtn["state"] = "normal"
                self.upBtn["state"] = "normal"
                self.eqPEnt["state"] = "normal"
                self.eqPBtn["state"] = "normal"
                self.doneBtn["state"] = "normal"
                self.setPntBtn["state"] = "normal"
                self.abortBtn["state"] = "normal"
                self.printBtn["state"] = "normal"

            driver.moveDropToCam(self.printLoc, cb)

        def setPnt(self):
            loc = driver.getStageXY()
            self.offset = (self.printLoc[0] - loc[0], self.printLoc[1] - loc[1])
            driver.saveOffset(self.printLoc[0] - loc[0], self.printLoc[1] - loc[1])
            # TODO: update calib dict
            CALIB_DICT["printer offset"].config(text=f"printer offset: {CALIBRATED}", background="#65d92b")


        def armUp(self):
            # moves up, cb disables all printing related buttons
            self.printBtn["state"] = "disabled"
            self.gotoBtn["state"] = "disabled"
            self.setPntBtn["state"] = "disabled"
            self.upBtn["state"] = "disabled"
            self.eqPBtn["state"] = "disabled"
            self.eqPEnt["state"] = "disabled"
            self.doneBtn["state"] = "disabled"
            interruptBtn["state"] = "normal"
            # moveToSafeBtn["state"] = "disabled"

            def cb():
                self.doneBtn["state"] = "normal"
                self.toChipBtn["state"] = "normal"
                interruptBtn["state"] = "disabled"
                # moveToSafeBtn["state"] = "normal"

            driver.moveArmToUp(cb)

        def abort(self):
            # TODO: this button / function may not be necessary
            # call interrupt, only enable done
            def cb():
                self.doneBtn["state"] = "normal"
            
            driver.interrupt(cb)

        def done(self):
            # cb(enable start, disable abort), done
            # move arm up
            self.doneBtn["state"] = "disabled"
            self.upBtn["state"] = "disabled"
            self.toChipBtn["state"] = "disabled"
            self.printBtn["state"] = "disabled"
            self.eqPBtn["state"] = "disabled"
            self.eqPEnt["state"] = "disabled"
            self.setPntBtn["state"] = "disabled"
            interruptBtn["state"] = "normal"
            # moveToSafeBtn["state"] = "disabled"

            def cb():
                self.startBtn["state"] = "normal"
                self.abortBtn["state"] = "disabled"
                for btn in self.calibButtons: btn["state"] = "normal"
                interruptBtn["state"] = "disabled"
                # moveToSafeBtn["state"] = "normal"

            driver.moveArmToUp(cb)

  
class SanityMenu(ttk.Frame):
    def __init__(self, parent):
        ttk.Frame.__init__(self, parent)
        for i in range(3): self.rowconfigure(i, weight=1)
        self.columnconfigure(0, weight=1)
        self.sanity_buttons = []

        # TODO: interrupt button, print drop to channel, print row of drops in place

        overWell = self.OverWell(self, self.sanity_buttons)
        grid(overWell, 0,0,5,5)

        overChannel = self.OverChannel(self, self.sanity_buttons)
        grid(overChannel, 1,0,5,5)

        showChannel = self.ChanOnCam(self, self.sanity_buttons)
        grid(showChannel, 2,0,5,5)

        grabSample = self.GrabSample(self, self.sanity_buttons)
        grid(grabSample,3,0,5,5)

        printRow = self.PrintRow(self, self.sanity_buttons)
        grid(printRow, 4, 0, 5, 5)

        printChan = self.PrintChan(self, self.sanity_buttons)
        grid(printChan, 5, 0, 5, 5)
        
    class OverWell(ttk.LabelFrame):
        def __init__(self, parent, buttons):
            ttk.LabelFrame.__init__(self, parent, text="Test head above well")
            for i in range(3): 
                self.rowconfigure(i, weight=1)
                self.columnconfigure(i, weight=1)

            self.sanity_buttons = buttons

            wellLab = ttk.Label(self, text="Select well: (ex: A1)")
            grid(wellLab, 0,0,0,0)

            self.wellEnt = ttk.Entry(self)
            grid(self.wellEnt,0,1,0,0)

            goBtn = ttk.Button(self, text="go above well", command=self.goWell)
            goBtn.grid(row=1,column=0, columnspan=2, sticky='nsew')

            self.downBtn = ttk.Button(self, text="go into well", command=self.headIntoWell)
            self.downBtn.grid(row=2,column=0, columnspan=2, sticky='nsew')
            self.downBtn["state"] = "disabled"


            self.upBtn = ttk.Button(self, text="done", command=self.headUp)
            self.upBtn.grid(row=3,column=0, columnspan=2, sticky='nsew')
            self.upBtn["state"] = "disabled"

            self.sanity_buttons.extend([wellLab, self.wellEnt, goBtn])

        def goWell(self):
            def cb(): 
                interruptBtn["state"] = "disabled"
                self.downBtn["state"] = "normal"
                self.upBtn["state"] = "normal"

            well = self.wellEnt.get()

            try:
                for btn in self.sanity_buttons: btn["state"] = "disabled"
                interruptBtn["state"] = "normal"
                # moveToSafeBtn["state"] = "disabled"

                driver.movePrinterOverWell(well, cb)
            except Exception as e:
                messagebox.showerror(title="Going over well failed", message=f"error: {str(e)}")

        def headIntoWell(self):
            def cb():
                interruptBtn["state"] = "disabled"

            self.downBtn["state"] = "disabled"
            interruptBtn["state"] = "normal"
            for btn in self.sanity_buttons: btn["state"] = "disabled" 
            driver.movePrinterIntoWell(cb)

        def headUp(self):
            def cb():
                interruptBtn["state"] = "disabled"
                for btn in self.sanity_buttons: btn["state"] = "normal"
            
            interruptBtn["state"] = "normal"
            self.downBtn["state"] = "disabled"
            self.upBtn["state"] = "disabled"
            driver.moveArmToUp(cb)


    class OverChannel(ttk.LabelFrame):
        def __init__(self, parent, buttons):
            ttk.LabelFrame.__init__(self, parent, text="Test head above channel")
            # TODO: have a button to move it back up, only enable buttons after moved up
            for i in range(4): 
                self.rowconfigure(i, weight=1)
                self.columnconfigure(i, weight=1)

            self.sanity_buttons = buttons

            chanLab = ttk.Label(self, text="Select channel: (ex: 22)")
            grid(chanLab, 0,0,0,0)

            self.chanEnt = ttk.Entry(self)
            grid(self.chanEnt,0,1,0,0)

            goBtn = ttk.Button(self, text="go above channel",command=self.aboveChan)
            goBtn.grid(row=1,column=0, columnspan=2, sticky='nsew')

            self.sanity_buttons.extend([chanLab, self.chanEnt, goBtn])

            self.downBtn = ttk.Button(self, text="move down to chip", command=self.moveDown)
            self.downBtn.grid(row=2, column=0, columnspan=2, stick='nsew')
            self.downBtn["state"] = "disabled"

            # arm needs to move back up when done
            self.upBtn = ttk.Button(self, text="done", command=self.moveUp)
            self.upBtn.grid(row=3, column=0, columnspan=2, stick='nsew')
            self.upBtn["state"] = "disabled"


            # for child in self.winfo_children(): self.sanity_buttons.append(child)
        
        def aboveChan(self):
            def cb(): 
                self.downBtn["state"] = "normal"
                self.upBtn["state"] = "normal"
                interruptBtn["state"] = "disabled"
                # moveToSafeBtn["state"] = "normal"
            chan = self.chanEnt.get()
            try:
                chan = int(chan)
                interruptBtn["state"] = "normal"
                # moveToSafeBtn["state"] = "disabled"
                for btn in self.sanity_buttons: btn["state"] = "disabled"
                driver.movePrinterOverChannel(chan, cb)
            except ValueError as e:
                print(e)
                messagebox.showerror(title="Invalid Channel", message=f"{chan} is not a valid channel")

        def moveDown(self):
            def cb():
                interruptBtn["state"] = "disabled"
                # moveToSafeBtn["state"] = "normal"
                self.upBtn["state"] = "normal"
            self.downBtn["state"] = "disabled"

            driver.movePrinterToChip(cb)

        def moveUp(self):
            def cb(): 
                for btn in self.sanity_buttons: btn["state"] = "normal"
            self.upBtn["state"] = "disabled"
            driver.moveArmToUp(cb) 

    class ChanOnCam(ttk.Labelframe):
        def __init__(self, parent, buttons):
            ttk.LabelFrame.__init__(self, parent, text="Show channel on camera")
            for i in range(2): 
                self.rowconfigure(i, weight=1)
                self.columnconfigure(i, weight=1)

            self.sanity_buttons = buttons
            chanLab = ttk.Label(self, text="Select channel: (ex: 22)")
            grid(chanLab, 0,0,0,0)

            self.chanEnt = ttk.Entry(self)
            grid(self.chanEnt,0,1,0,0)

            showBtn = ttk.Button(self, text="show channel", command=self.showChan)
            self.sanity_buttons.append(showBtn)
            showBtn.grid(row=1,column=0, columnspan=2, sticky='nsew')

        def showChan(self):
            # TODO: make a good callback
            def cb(): 
                for btn in self.sanity_buttons: btn["state"] = "normal"

            chan = self.chanEnt.get()
            try:
                chan = int(chan)
                for btn in self.sanity_buttons: btn["state"] = "disabled"
                driver.focusChannel(chan, cb)
            except:
                messagebox.showerror(title="Invalid Channel", message=f"{chan} is not a valid channel")

    class GrabSample(ttk.LabelFrame):
        def __init__(self, parent, buttons):
            ttk.LabelFrame.__init__(self, parent, text="Test Grabbing a Sample")
            for i in range(2): 
                self.rowconfigure(i, weight=1)
                self.columnconfigure(i, weight=1)

            self.sanity_buttons = buttons

            wellLab = ttk.Label(self, text="Select well: (ex: A1)")
            grid(wellLab, 0,0,0,0)

            wellEnt = ttk.Entry(self)
            grid(wellEnt,0,1,0,0)

            goBtn = ttk.Button(self, text="get sample from well")
            goBtn.grid(row=1,column=0, columnspan=2, sticky='nsew')

            for child in self.winfo_children(): self.sanity_buttons.append(child)

    class PrintRow(ttk.LabelFrame):
        def __init__(self, parent, sanityButtons):
            ttk.LabelFrame.__init__(self, parent, text="Print a row of drops to current position")
            self.sanityButtons = sanityButtons

            lab = ttk.Label(self, text="number of drops")
            grid(lab, 0, 0, 5, 5)
            self.dropsEnt = ttk.Entry(self)
            grid(self.dropsEnt,0, 1, 5, 5)

            goBtn = ttk.Button(self, text="print drops", command=self.printDrops)
            goBtn.grid(row=1, column=0, columnspan=2, sticky='nsew', padx=5, pady=5)
            # TODO: add these buttons to sanity buttons
            self.sanityButtons.extend([lab, self.dropsEnt, goBtn])

        def printDrops(self):
            num = self.dropsEnt.get()
            try:
                num = int(num)
                if num < 1 or num > 10:
                    messagebox.showerror(title="bad number of drops", message="please enter an integer between 1 and 10 (inclusive)")
                    return
                
                # TODO: cb - disable other sanity menu items
                def cb():
                    for btn in self.sanityButtons: btn["state"] = "normal"

                for btn in self.sanityButtons: btn["state"] = "disabled"
                driver.testPrintMultipleDrops(num, cb)

            except Exception as e:
                messagebox.showerror(title="method failed", message=f"{str(e)}")

    class PrintChan(ttk.LabelFrame):
        def __init__(self, parent, buttons):
            ttk.LabelFrame.__init__(self, parent, text= 'Print to specific channel')
            
            self.sanity_buttons = buttons
            lab = ttk.Label(self, text="select channel (ex: 22)")
            grid(lab, 0, 0, 0, 0)

            self.chanEnt = ttk.Entry(self)
            grid(self.chanEnt, 0, 1, 0, 0)

            self.goBtn = ttk.Button(self, text="print to channel", command=self.printToChan)
            self.goBtn.grid(row = 1, column = 0, columnspan=2, sticky='nsew')

            self.sanity_buttons.extend([lab, self.chanEnt, self.goBtn])

        def printToChan(self):
            chan = self.chanEnt.get()
            try:
                chan = int(chan)
                def cb():
                    for btn in self.sanity_buttons: btn["state"] = "normal"
                for btn in self.sanity_buttons: btn["state"] = "disabled"

                driver.testPrintDropToChan(chan, cb)
            except Exception as e:
                messagebox.showerror(title="error", message=f"{str(e)}")

class CalibratedList(ttk.LabelFrame):
    def __init__(self, parent, calibrations):
        
        ttk.LabelFrame.__init__(self, parent, text="Calibration Status")
        self.calibrations = calibrations
        self.calibrations["arm"] = ttk.Label(self, text=f"arm: {NOT_CALIBRATED}", background="#de4543")
        self.calibrations["arm"].pack(expand=True, fill='both')

        self.calibrations["stage"] = ttk.Label(self, text=f"stage: {LOADED}", background="#e39919")
        self.calibrations["stage"].pack(expand=True, fill='both')

        self.calibrations["printer offset"] = ttk.Label(self, text=f"printer offset: {LOADED}", background="#e39919")
        self.calibrations["printer offset"].pack(expand=True, fill='both')

        self.calibrations["first channel"] = ttk.Label(self, text=f"first channel: {LOADED}", background="#e39919")
        self.calibrations["first channel"].pack(expand=True, fill='both')

        self.calibrations["first well"] = ttk.Label(self, text=f"first well: {LOADED}", background="#e39919")
        self.calibrations["first well"].pack(expand=True, fill='both')

        self.calibrations["pressures"] = ttk.Label(self, text=f"pressures: {LOADED}", background="#e39919")
        self.calibrations["pressures"].pack(expand=True, fill='both')

        for child in self.winfo_children(): STARTUP_DISABLED_BUTTONS.append(child)

class AdditionalCommands(ttk.LabelFrame):
    def __init__(self, parent):
        ttk.LabelFrame.__init__(self, parent, text="Additional Commands")
        for i in range(6): self.rowconfigure(i, weight=1)
        self.columnconfigure(0, weight=1)

        self.camOpen = False
        self.chanOpen = False
        self.lowOpen = False

        grid(FocusChannel(self), 0, 0,0,0)

        showCamBtn = ttk.Button(self, text="open camera display", command=self.openCamera)
        grid(showCamBtn, 1, 0, 0, 0)

        cleanHeadBtn = ttk.Button(self, text="clean the printer head")
        ARM_ENABLES.append(cleanHeadBtn)
        grid(cleanHeadBtn, 2, 0 ,0 ,0)

        showChannelContents = ttk.Button(self, text="show channel contents", command = self.openChannels)
        grid(showChannelContents, 3, 0, 0, 0)
        STARTUP_DISABLED_BUTTONS.append(showChannelContents)

        openMenu = ttk.Button(self, text="open low-level command menu", command=self.openLowMenu)
        grid(openMenu, 4, 0, 0, 0)
        # STARTUP_DISABLED_BUTTONS.append(openMenu) # TODO: maybe uncomment this

    def openCamera(self):
        def on_closing():
            # if not self.cw.stopCamThreads:
            # self.cw.stopCamThreads = True
            cameraWin.destroy()
            self.camOpen = False
            # else:
                # messagebox.showerror(title="cannot close camera window", message="Please click 'stop camera feed' before closing window")

        if not self.camOpen:
            cameraWin = tk.Toplevel(root)
            cameraWin.title("Camera Display")
            self.cw = CamWidget(cameraWin)
            grid(self.cw , 0,0,0,0)
            cameraWin.protocol("WM_DELETE_WINDOW", on_closing)
            self.camOpen = True

    def openLowMenu(self):
        def on_closing():
            lowWin.destroy()
            self.lowOpen = False

        if not self.lowOpen:
            lowWin = tk.Toplevel(root)
            lowWin.title("low level commands")
            am = AdditionalMenu(lowWin)
            grid(am, 0,0,0,0)
            lowWin.protocol("WM_DELETE_WINDOW", on_closing)
            self.lowOpen = True


    def openChannels(self):
        def on_closing():
            chanWin.destroy()
            self.chanOpen = False

        if not self.chanOpen:
            chanWin = tk.Toplevel(root)
            chanWin.title("Channel Contents")
            grid(ChannelContents(chanWin), 0,0,0,0)

            chanWin.protocol("WM_DELETE_WINDOW", on_closing)
            self.chanOpen = True

class AdditionalMenu(ttk.Frame):
    # NOTE: This is just for when you want no automation but still want to control most things. pretty much all commands are nonblocking
    """ 
    Menu for issuing any low level commands and anything else we can think of
    """
    def __init__(self, parent):
        ttk.Frame.__init__(self, parent)
        # move arm in mm, which will allow floats. Also calibrate arm (move to top), move to absolute z position in steps. print pos to console
            # labelframe, entry, button
        armFrame = ttk.LabelFrame(self, text="move arm")
        for i in range(4): armFrame.rowconfigure(i, weight=1)
        armFrame.columnconfigure(0, weight=1)

        relMMFrame = ttk.LabelFrame(armFrame, text="relative arm move (mm)")
        for i in range(2): relMMFrame.columnconfigure(i, weight=1)
        self.armEnt = ttk.Entry(relMMFrame)
        armBtn = ttk.Button(relMMFrame, text="move (relative, mm)", command=self.moveArm)

        aoBtn = ttk.Button(armFrame, text="calibrate origin", command=self.calibOrigin)
        
        absFrame = ttk.LabelFrame(armFrame, text="absolute arm move")
        for i in range(4): absFrame.rowconfigure(i, weight=1)
        absFrame.columnconfigure(0, weight=1)

        self.armSEnt = ttk.Entry(absFrame)
        armSBtn = ttk.Button(absFrame, text="move to absolute (in steps)", command=self.moveInSteps)

        self.armMEnt = ttk.Entry(absFrame)
        armMBtn = ttk.Button(absFrame, text="move to absolute (in mm)", command=self.moveAbsMM)

        stepbtn = ttk.Button(absFrame, text="Get current arm position", command=self.getZPos)
        intBtn = ttk.Button(absFrame, text="interrupt arm movement", command=self.intteruptArm)
        absFrame.grid(row=2, column=0, columnspan=2, sticky='nsew')

        aoBtn.grid(row=0, column=0, columnspan=2, padx=5, pady=5, sticky='nsew')
        grid(self.armEnt, 0, 0, 5, 5)
        grid(armBtn, 0, 1, 5, 5)
        relMMFrame.grid(row=1, column=0, columnspan=2, sticky='nsew')
        grid(self.armSEnt, 0, 0, 5, 5)
        grid(armSBtn, 0, 1, 5, 5)
        grid(self.armMEnt, 1, 0, 5, 5)
        grid(armMBtn, 1, 1, 5, 5)



        stepbtn.grid(row=2, column=0, columnspan=2, padx=5, pady=5, sticky='nsew')
        intBtn.grid(row=3, column=0, columnspan=2, padx=5, pady=5, sticky='nsew')
        grid(armFrame,0, 0, 5, 5)

        # apply certain pressure for certain num of seconds
            # labelframe, entry, entry, button
        paFrame = ttk.LabelFrame(self, text="apply certain pressure for certain amount of time")
        for i in range(2):
            paFrame.columnconfigure(i, weight=1)
            paFrame.rowconfigure(i, weight=1)
        palab = ttk.Label(paFrame, text="pressure (mbar)")
        self.paEnt = ttk.Entry(paFrame)
        secLab = ttk.Label(paFrame, text="seconds")
        applyPressureBtn = ttk.Button(paFrame, text="apply pressure", command=self.applyPressure)
        self.secEnt = ttk.Entry(paFrame)

        grid(palab, 0, 0, 5, 5)
        grid(self.paEnt, 0, 1, 5, 5)
        grid(secLab, 1, 0, 5, 5)
        grid(self.secEnt, 1, 1, 5, 5)
        applyPressureBtn.grid(row=2, column=0, columnspan=2, padx=5, pady=5, sticky='nsew')
        grid(paFrame, 1,0,5,5)

        # trigger jetserver
            # labelframe, button

        # set pressure for undefined amount of time (equilibrium pressure, in, out)
            # labelframe, entry, button, stop button (set to zero)
        self.steadyPFrame = ttk.LabelFrame(self, text="set constant pressure (mbar)")
        for i in range(2):
            self.steadyPFrame.rowconfigure(i, weight=1)
            self.steadyPFrame.columnconfigure(i, weight=1)
        self.steadyPent = ttk.Entry(self.steadyPFrame)
        self.steadyPBtn = ttk.Button(self.steadyPFrame, text="set this as pressure", command=self.setSteady)
        steadyStopBtn = ttk.Button(self.steadyPFrame, text="set pressure to 0", command=self.clearSteady)
        grid(self.steadyPFrame, 3, 0, 5,5)
        grid(self.steadyPent, 0,0,5,5)
        grid(self.steadyPBtn, 0,1,5,5)
        steadyStopBtn.grid(row=1, column=0, columnspan=2, padx=5, pady=5, sticky='nsew')

        # offset calibration menu
            # labelframe, print button, set button, goto button
            # stores self.printloc
        offFrame = ttk.LabelFrame(self, text="offset calibration")
        for i in range(2): 
            offFrame.rowconfigure(i, weight=1)
            offFrame.columnconfigure(i, weight=1)
        self.printLoc = (None, None)
        printBtn = ttk.Button(offFrame, text="print drop, save location", command=self.triggerJet)
        saveOffBtn = ttk.Button(offFrame, text="save offset (set point)", command=self.setPnt)
        gotoBtn = ttk.Button(offFrame, text="show drop on cam", command=self.dropOnCam) # offset must be good first
        grid(offFrame, 4, 0, 5,5)
        grid(printBtn, 0,0,5,5)
        grid(gotoBtn, 1,0,5,5)
        saveOffBtn.grid(row=0, column=1, rowspan=2, padx=5, pady=5, sticky='nsew')

        stageFrame = ttk.LabelFrame(self, text="stage movement")
        for i in range(3): stageFrame.rowconfigure(i, weight=1)
        for i in range(2): stageFrame.columnconfigure(i, weight=1)
        saveFirstBtn = ttk.Button(stageFrame, text="save position as first channel on camera", command=self.saveFirstChan)
        self.chanToCamEnt = ttk.Entry(stageFrame)
        chanToCamBtn = ttk.Button(stageFrame, text="show channel on camera", command=self.chanToCam)
        self.chanToPEnt = ttk.Entry(stageFrame)
        chanToPBtn = ttk.Button(stageFrame, text="move channel to printer", command=self.chanToPrinter)

        grid(stageFrame, 5, 0, 5, 5)
        grid(saveFirstBtn, 0, 0, 5, 5)
        saveFirstBtn.grid(row=0, column=0, columnspan=2, padx=5, pady=5)
        grid(self.chanToCamEnt, 1, 0, 5, 5)
        grid(chanToCamBtn, 1, 1, 5, 5)
        grid(self.chanToPEnt, 2, 0, 5, 5)
        grid(chanToPBtn, 2, 1, 5, 5)    

        toKFrame = ttk.LabelFrame(self, text="print to at most 40 channels, starting from the first channel")
        toKFrame.rowconfigure(0, weight=1)
        toKFrame.columnconfigure(0, weight=1)
        self.toKEnt = ttk.Entry(toKFrame)
        toKBtn = ttk.Button(toKFrame, text="start printing", command=self.printToK)
        grid(self.toKEnt, 0, 0, 5, 5)
        grid(toKBtn, 0, 1, 5, 5)
        grid(toKFrame, 6, 0, 5, 5)

        toCamBtn = ttk.Button(self, text="print to current camera position", command=self.printToCam)

        grid(toCamBtn, 7, 0, 5, 5)

        self.buttons = [self.armEnt, armBtn, aoBtn, self.armSEnt, armSBtn, stepbtn, applyPressureBtn, 
                        steadyStopBtn, printBtn, saveOffBtn, gotoBtn, saveFirstBtn, chanToCamBtn, 
                        chanToPBtn, toKBtn, self.steadyPBtn, self.armMEnt, armMBtn]

    def printToK(self):
        num = self.toKEnt.get()
        try:
            num = int(num)
            def cb():
                for btn in self.buttons: btn["state"] = "normal"
            
            if (num < 0 or num > driver.microscope.chip.numChan):
                messagebox.showerror(title="bad number of channels", message="too many or too few channels")
                return

            for btn in self.buttons: btn["state"] = "disabled"
            driver.printCurrToK(num, cb)
        except Exception as e:
            messagebox.showerror(title="something went wrong", message=str(e))

    def printToCam(self):
        def cb(): 
            for btn in self.buttons: btn["state"] = "normal"
        for btn in self.buttons: btn["state"] = "disabled"
        driver.printToCam(cb)

    def moveAbsMM(self):
        mm = self.armMEnt.get()
        try:
            mm = float(mm)
            def cb():
                for btn in self.buttons: btn["state"] = "normal"
            for btn in self.buttons: btn["state"] = "disabled"
            driver.moveToZAbsoluteInUM(mm * 1000, cb)
        except Exception as e:
            messagebox.showerror(title="error", message=str(e))

    def intteruptArm(self):
        def fakecb():print("interrupting complete")
        driver.interrupt(fakecb)

    def moveArm(self):
        mm = self.armEnt.get()
        def cb():
            for btn in self.buttons: btn["state"] = "normal"            
        try:
            mm = float(mm)

            for btn in self.buttons: btn["state"] = "disabled"            
            driver.moveToZRelInUM(mm * 1000, cb)
        except Exception as e:
            print(e)

    def calibOrigin(self):
        try:
            def cb():
                for btn in self.buttons: btn["state"] = "normal"      
            for btn in self.buttons: btn["state"] = "disabled"            
            driver.calibrateZArm(cb)
        except:
            messagebox.showerror(title="error", message="please connect to the device first")

    def moveInSteps(self):
        steps = self.armSEnt.get()

        def cb():
            for btn in self.buttons: btn["state"] = "normal"    
        try:
            steps = int(steps)
            for btn in self.buttons: btn["state"] = "disabled"    
            driver.moveToZInSteps(steps, cb)
        except Exception as e:
            print(e)
    
    def getZPos(self):
        inum = driver.microscope.arm.zmotor.getZPosInUM()
        mess = f"steps: {driver.microscope.arm.zmotor.getZPosInSteps()}\num: {inum}\nmm: {inum / 1000}"
        messagebox.showinfo(title="Arm position", message=mess)
        print(f"steps: {driver.microscope.arm.zmotor.getZPosInSteps()}")
        print(f"um: {inum}")
        print(f"mm: {inum / 1000}")

    def applyPressure(self):
        pressure = self.paEnt.get()
        seconds = self.secEnt.get()
        try:
            pressure = float(pressure)
            seconds = float(seconds)
            driver.microscope.printer.pressure.pcontroller.set_pressure(4, pressure)
            sleep(seconds)
            driver.microscope.printer.pressure.pcontroller.set_pressure(4, 0)
        except Exception as e:
            print(e)

    def setSteady(self):
        steadyP = self.steadyPent.get()
        try:
            steadyP = float(steadyP)
            driver.microscope.printer.pressure.pcontroller.set_pressure(4, steadyP)
        except Exception as e:
            print(e)

    def clearSteady(self):
            driver.microscope.printer.pressure.pcontroller.set_pressure(4, 0)

    def triggerJet(self):
        driver.microscope.printer.printSingleDrop()
        self.printLoc=driver.getStageXY()

    def setPnt(self):
        loc = driver.getStageXY()
        driver.saveOffset(self.printLoc[0] - loc[0], self.printLoc[1] - loc[1])
    
    def dropOnCam(self):
        def cb():
            for btn in self.buttons: btn["state"] = "normal"    
        
        for btn in self.buttons: btn["state"] = "disabled"    
        driver.moveDropToCam(self.printLoc, cb)

    def saveFirstChan(self):
        driver.saveFirstChannelCamPos()
    
    def chanToCam(self):
        chan = self.chanToCamEnt.get()
        try:
            chan = int(chan)
            def cb():
                for btn in self.buttons: btn["state"] = "normal"    
        
            for btn in self.buttons: btn["state"] = "disabled"    
            driver.focusChannelNoLift(chan, cb)
        except Exception as e:
            print(e)
    
    def chanToPrinter(self):
        chan = self.chanToPEnt.get()
        try:
            chan = int(chan)
            def cb():
                for btn in self.buttons: btn["state"] = "normal"    
        
            for btn in self.buttons: btn["state"] = "disabled"    
            driver.chanToPrinterNoLift(chan, cb)
        except Exception as e:
            print(e)

class ChannelContents(ttk.Frame):
    def __init__(self, parent):
        ttk.Frame.__init__(self, parent)
        grid(ttk.Label(self, text="this is a placeholder for channel contents popup"), 0 ,0,0,0)
        grid(ttk.Label(self, text=f"{driver.microscope.chip.getAllChannelContents()}"), 1 ,0,0,0)
        grid(ttk.Label(self, text=f"{[i for i in range(1, driver.microscope.chip.numChan + 1)]}"), 2 ,0,0,0)
        #TODO: make a good channel contents widget

    
class FocusChannel(ttk.LabelFrame):
    def __init__(self, parent):
        ttk.LabelFrame.__init__(self, parent, text="Show Channel on camera")
        self.rowconfigure(0, weight=1)
        self.columnconfigure(0, weight=1)
        self.columnconfigure(1, weight=1)

        self.chanEnt = ttk.Entry(self)
        ARM_ENABLES.append(self.chanEnt)
        grid(self.chanEnt, 0, 0, 0, 0)

        goBtn = ttk.Button(self, text="focus", command = self.focus)
        ARM_ENABLES.append(goBtn)
        grid(goBtn, 0,1,0,0)

    def focus(self):
        def cb():
            for item in DISABLE_BUTTONS: item["state"] = "normal"
        chan = self.chanEnt.get()
        try:
            chan = int(chan)
            driver.focusChannel(chan, cb)
        except ValueError:
            messagebox.showwarning(title="invalid channel", message=f"please enter a channel between 1 and {driver.microscope.chip.numChan}")
    

root.grid_columnconfigure(0, weight=1)
root.grid_columnconfigure(1, weight=1)
root.grid_rowconfigure(0, weight=1)
root.grid_rowconfigure(1, weight=1)

hl = HighLevel(root)
hl.grid(row=0, column=0, rowspan=2, sticky='nsew', padx=5, pady=5)

calib = CalibrationFrame(root)
grid(calib, 0, 1, 5, 5)

additional = AdditionalCommands(root)
grid(additional,1,1,5,5)

def fakeCB(): x=3

for item in STARTUP_DISABLED_BUTTONS: item["state"] = "disabled"
for item in ARM_ENABLES: item["state"] = "disabled"


def close_main():
    def closeCB(): x=3
    if (additional.camOpen):
        messagebox.showerror(title="Camera open", message="Please close the camera display before closing the main GUI. This is to prevent a bug.")
    else:

        if driver != None:
            driver.close(closeCB)
            print("driver closed")
        else:
            closeCB()

        root.destroy()

root.protocol("WM_DELETE_WINDOW", close_main)

root.mainloop()
