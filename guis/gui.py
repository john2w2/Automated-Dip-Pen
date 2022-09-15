from cgitb import text
from email import message
import tkinter as tk
import sys
sys.path.append("C:/Users/19199/Desktop/automated-sca/src")

import serial

from tkinter import Button, ttk
from tkinter import messagebox
from time import sleep
from threading import Thread
from microscopeDriver import MicroscopeDriver
from gui_widgets.camWidget import CamWidget
from gui_widgets.wellSelect import WellSelect

# from microscopeDriver import MicroscopeDriver

driver: MicroscopeDriver = None
DISABLE_BUTTONS = []  # list of buttons that should be disabled for most commands
STARTUP_DISABLED_BUTTONS = [] # list of buttons that should be disabled before startup, enabled once startup succeeds
CALIB_DICT = {} # dictionary mapping device name to calibration status
CALIBRATED = "calibrated"
NOT_CALIBRATED = "not calibrated"
LOADED = "loaded from previous run"

interruptBtn: ttk.Button = None # global reference to interrupt button
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

        interruptBtn = ttk.Button(self, text="INTERRUPT")
        grid(interruptBtn, 1, 0, 5, 5)
        interruptBtn["state"] = "disabled"

        self.singleToMultiple = SingleToMultiple(self)
        grid(self.singleToMultiple, 2, 0, 5, 5, sticky='ew')

        self.toK = PrintEachToK(self)
        grid(self.toK, 3, 0, 5, 5, sticky='ew')

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
        pass

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

        for child in self.winfo_children(): STARTUP_DISABLED_BUTTONS.append(child)

    #TODO: function to call printing, handling bad input with message box

    def getWellInput():
        pass

    def getChannelInput():
        pass

class PrintEachToK(ttk.Labelframe):
    def __init__(self, parent):
        ttk.LabelFrame.__init__(self, parent, text="Print Samples to K")
        for i in range(4): self.rowconfigure(i, weight=1)
        self.columnconfigure(0, weight=1)

        self.wellSelectOpen = False

        self.openWellsBtn = ttk.Button(self, text="open well select menu", cursor="hand2", command=self.openWellSelectMenu)
        grid(self.openWellsBtn, 0, 0, 5, 5)

        self.selectedWellsList = ttk.Label(self, text="selected wells:")
        grid(self.selectedWellsList, 1, 0, 5, 5)

        kLabel = ttk.Label(self, text="number of channels for each sample")
        grid(kLabel, 2, 0, 5, 5)

        self.kEnt = ttk.Entry(self)
        grid(self.kEnt, 3, 0, 5, 5)

        goBtn = ttk.Button(self, text="start")
        grid(goBtn, 4, 0, 0,0)

        for child in self.winfo_children(): STARTUP_DISABLED_BUTTONS.append(child)

    #TODO: function to call printing, handling bad input
    #TODO: some way to get selected from welLSelect (some array stored in PrintEachToK, pass to wellselect)

    def openWellSelectMenu(self):
        def on_closing():
                wellSelectMenu.destroy()
                self.wellSelectOpen = False

        if not self.wellSelectOpen:
            wellSelectMenu = tk.Toplevel(root)
            wellSelectMenu.title("Well Select Menu")
            # NOTE: WellSelect is an imported class
            grid(WellSelect(wellSelectMenu), 0,0,0,0)
            # TODO: this also needs buttons to save or cancel selection
            # TODO: wellselect save button should close window, put wells in array using WellSelect.getSelected
            wellSelectMenu.protocol("WM_DELETE_WINDOW", on_closing)
            self.wellSelectOpen = True

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
        STARTUP_DISABLED_BUTTONS.append(openSanity)
        grid(openSanity, 1, 0, 5, 5)

        self.calibList = CalibratedList(self, CALIB_DICT)
        grid(self.calibList, 2, 0, 5, 5)


    def openCalibMenu(self):
        def on_closing():
            self.calibMenu.destroy()
            self.calibOpen = False

        if not self.calibOpen:
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
            sanityMenu.destroy()
            self.sanityOpen = False

        if not self.sanityOpen:
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
        self.calibArmBtn = ttk.Button(self, text="recalibrate arm Z axis", command=self.calibArm)
        self.calibArmBtn.grid(row=0, column=0, rowspan=1, sticky='nsew')

        stageCal = self.StageCalibration(self, self.buttons)
        # grid(stageCal, 1, 0,5,5)
        stageCal.grid(row=1, column=0, rowspan=4, sticky='nsew')

        printDrop = self.PrintDropTest(self, self.buttons)
        # grid(printDrop, 2, 0, 5,5 )
        printDrop.grid(row=5, column=0, rowspan=5, sticky='nsew')

        getSample = self.ManualGetSample(self, self.buttons)
        getSample.grid(row=0, column=1, rowspan=2, sticky='nsew', padx=5, pady=5)
        # grid(getSample, 0, 1, 5, 5)

        self.offset = self.OffSetCalibration(self, self.buttons)
        # grid(self.offset, 4, 1, 5,5)
        self.offset.grid(row=2, column=1, rowspan=2, sticky='nsew', padx=5, pady=5)


        pressureCal = self.PressureCalibration(self, self.buttons)
        # grid(pressureCal, 5, 1, 5, 5)
        pressureCal.grid(row=4, column=1, rowspan=2, sticky='nsew', padx=5, pady=5)


        for item in self.buttons: item["state"] = "disabled"



    def calibArm(self):
        """ recalibrates the z axis arm """

        for btn in self.buttons: btn["state"] = "disabled"
        self.calibArmBtn["state"] = "disabled"
        # self.offset.getStartBtn()["state"] = "disabled"

        def cb():
            for btn in self.buttons: btn["state"] = "normal"
            self.offset.getStartBtn()["state"] = "normal"
            CALIB_DICT["arm"].config(text=f"arm: {CALIBRATED}", background="#65d92b")
            self.buttons.append(self.calibArmBtn)
            for item in self.buttons: item["state"] = "normal"

        driver.calibrateZArm(cb)

    def recalibratePressureSystem(self):
        """ recalibrates the pressure sytem (make sure you have caps on)"""
        for btn in self.buttons: btn["state"] = "disabled"
        self.offset.getStartBtn()["state"] = "disabled"

        def cb():
            for btn in self.buttons: btn["state"] = "normal"
            self.offset.getStartBtn()["state"] = "normal"

        def fakeThread(cb): sleep(1); cb()

        # driver.recalibratePressure()
        # mimic calling driver
        t=Thread(target=fakeThread, args=[cb])
        t.start()

    class StageCalibration(ttk.LabelFrame):
        def __init__(self, parent, calibButtons):
            ttk.Labelframe.__init__(self, parent, text="Stage Calibration")
            self.calibStageFrame = ttk.Labelframe(self, text="Positioning")

            resetStageLab = ttk.Label(self.calibStageFrame, text="move stage until it hits the bottom and right limit \n switches, then hit \n \"recalibrate stage positioning\"")
            grid(resetStageLab, 0, 0, 5, 5)
            self.resetStageBtn = ttk.Button(self.calibStageFrame, text="recalibrate stage positioning", command=self.resetStagePositioning)
            grid(self.resetStageBtn, 1,0,5,5)

            grid(self.calibStageFrame, 0, 0, 5, 5)

            self.firstChanBtn = ttk.Button(self, text="save current position as 'first channel on camera'", command=self.saveFirstChannelCamPos)
            grid(self.firstChanBtn, 1, 0, 5, 5)

            self.firstWellBtn = ttk.Button(self, text="save current position as 'first well centered on camera'", command=self.saveFirstWellCamPos)
            grid(self.firstWellBtn, 2,0,5,5)
            calibButtons.extend([self.resetStageBtn, self.firstChanBtn, self.firstWellBtn])

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

            eqPLab = ttk.Label(self.pressureFrame, text="Equilibrium pressure")
            self.eqPEnt = ttk.Entry(self.pressureFrame)
            self.eqPEnt.insert(0, "0")
            grid(eqPLab, 1, 0, 5, 0)
            grid(self.eqPEnt, 1, 1, 5, 0)

            outPLab = ttk.Label(self.pressureFrame, text="Out pressure")
            self.outPEnt = ttk.Entry(self.pressureFrame)
            self.outPEnt.insert(0, "80.0")
            grid(outPLab, 2, 0, 5, 0)
            grid(self.outPEnt, 2, 1, 5, 0)

            saveVals = ttk.Button(self.pressureFrame, text="Save pressure values", command=self.savePressures)
            saveVals.grid(row=3, column=0, columnspan=2, padx=5, pady=5)

            grid(self.pressureFrame, 1, 0, 5, 5)

            calibButtons.extend([self.calOB1, self.inPEnt, self.eqPEnt, self.outPEnt, saveVals])

        def calibOB1(self):
            def cb():
                # TODO: this shouldn't disable everything, just: get drop, save pressure values
                # well, for now it's ok to disable / re-enable everything
                # re-enable other calibration buttons
                for item in self.calibButtons: item["state"] = "normal"
                
            for item in self.calibButtons: item["state"] = "disabled"
            
            driver.recalibrateOB1(cb)

        def savePressures(self):
            # check if inputs are valid
            inP = self.inPEnt.get()
            eqP = self.eqPEnt.get()
            outP = self.outPEnt.get()
            try:
                inP = float(inP)
                eqP = float(eqP)
                outP = float(outP)
                driver.savePressures(inPressure=inP, eqPressure=eqP, outPressure=outP)
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

            def cb():
                self.moveOverWellBtn["state"] = "normal"
                self.instructions.configure(text="Move printer head above a well containing solution")


            driver.moveArmToUp(cb)
            
        def movedOverWell(self):
            self.moveOverWellBtn["state"] = "disabled"
            self.intoWellBtn["state"] = "normal"
            self.instructions.configure(text="press 'move into well'")

        def moveIntoWell(self):
            self.intoWellBtn["state"] = "disabled"
            #cb
            def cb():
                self.getSampleBtn["state"] = "normal"
                print("sample button normal")
                self.instructions.configure(text="press 'get sample'")

            driver.movePrinterIntoWell(cb)  

        def getSample(self):
            self.getSampleBtn["state"] = "disabled"
            def cb():
                self.moveUpBtn["state"] = "normal"
                self.instructions.configure(text="press 'move arm up'")

            driver.grabSampleNoMove(cb)

        def moveUp(self):
            self.moveUpBtn["state"] = "disabled"
            def cb():
                self.instructions.configure(text="There should now be a sample in the printer head.\nPress start to redo")
                self.abortBtn["state"] = "disabled"
                self.startBtn["state"] = "normal"
                for item in self.calibButtons: item["state"] = "normal"

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

            # what is the process here?
            #   start, edit equilibrium pressure, print, go to, set point, done (re-enable buttons)
            # oh, also down to chip, then up again buttons
            # just Kyler's menu pretty much
            self.instructions = ttk.Label(self, text="TBD, just a static description of each button")
            grid(self.instructions, 0, 0, 5, 0)

            self.startBtn = ttk.Button(self, text="start")
            grid(self.startBtn, 1, 0, 5, 0)

            self.toChipBtn = ttk.Button(self, text="move arm down to chip\n(make sure arm is above chip before)")
            grid(self.toChipBtn, 2, 0, 5, 0)
            self.toChipBtn["state"] = "disabled"

            # TODO: this should be its own frame (maybe)
            self.pressureFrame = ttk.LabelFrame(self, text="edit equilibrium pressure")
            for i in range(2): self.pressureFrame.columnconfigure(i, weight=1)
            self.eqPEnt = ttk.Entry(self.pressureFrame)
            grid(self.eqPEnt, 0, 0, 0, 0)
            self.eqPEnt["state"] = "disabled"
            self.eqPBtn = ttk.Button(self.pressureFrame, text="update") # save pressure value, then set to eqp pressure
            # NOTE: should probably limit eq pressure here between -20.0 to 20.0
            grid(self.eqPBtn, 0, 1, 0, 0)
            self.eqPBtn["state"] = "disabled"

            grid(self.pressureFrame, 3, 0, 5, 0)

            self.printBtn = ttk.Button(self, text="trigger print")
            grid(self.printBtn, 4, 0, 5, 0)
            self.printBtn["state"] = "disabled"

            self.gotoBtn = ttk.Button(self, text="show drop on cam ") # move arm up first
            grid(self.gotoBtn, 5, 0, 5, 0)
            self.gotoBtn["state"] = "disabled"

            self.setPntBtn = ttk.Button(self, text="set location as 'drop focused on camera'")
            grid(self.setPntBtn, 6, 0, 5, 0)
            self.setPntBtn["state"] = "disabled"

            self.upBtn = ttk.Button(self, text="move arm up")
            grid(self.upBtn, 7, 0, 5, 0)
            self.upBtn["state"] = "disabled"

            self.abortBtn = ttk.Button(self, text="abort process") # stops arm movement
            # only enables done button, which will have an implicit moveArmUp command called
            grid(self.abortBtn, 8, 0, 5, 0)
            self.abortBtn["state"] = "disabled"

            self.doneBtn = ttk.Button(self, text="done") 
            grid(self.doneBtn, 9, 0, 5, 0) 
            self.doneBtn["state"] = "disabled"

            calibButtons.append(self.startBtn)

        def start(self):
            pass

        def toChip(self):
            pass

        def saveEqP(self):
            pass

        def togglePrint(self):
            pass

        def goto(self):
            pass

        def setPnt(self):
            pass

        def armUp(self):
            pass

        def abort(self):
            pass

        def done(self):
            pass

    class OffSetCalibration(ttk.LabelFrame):
        # TODO: this will probably be deprecated by something else 
        def __init__(self, parent, calibButtons):
            ttk.LabelFrame.__init__(self, parent, text="Printer Offset")
            for i in range(5): self.rowconfigure(i, weight=1)

            self.columnconfigure(0, weight=1)
            self.infoLabel = ttk.Label(self, text="press start to begin", background="#eb584d")
            grid(self.infoLabel, 0, 0,0 ,0 )
            # disable all other buttons, pop up message saying "please move printer over waste slide, then hit print drop"
            self.startBtn = ttk.Button(self, text="start", command= self.startOffset)
            grid(self.startBtn, 1, 0,0 ,0)

            # print drop, save position, udpate message to "please move drop into + of camera"
            self.printBtn = ttk.Button(self, text="print drop", command=self.printDrop)
            grid(self.printBtn, 2, 0,0 ,0)
            self.printBtn["state"] = "disabled"
            # drop in cross, save position, then we're done
            self.focusBtn = ttk.Button(self, text="drop in center of +, save offset", command=self.dropFocused)
            grid(self.focusBtn, 3, 0, 0 ,0)
            self.focusBtn["state"] = "disabled"

            # abort button to stop the calibration if you want
            self.abortBtn = ttk.Button(self, text="abort offset calibration", command=self.abort)
            grid(self.abortBtn, 4, 0 ,0 ,0)
            self.abortBtn["state"] = "disabled"

            self.printLoc = (None, None)

            calibButtons.append(self.startBtn)

        def getStartBtn(self): 
            return self.startBtn
            
        def startOffset(self):
            """ disable all other calib GUI buttons, enable print drop button, enable abort"""
            # TODO: also disable all other calibration buttons
            for btn in self.otherButtons: btn["state"] = "disabled"
            self.abortBtn["state"] = "normal"
            self.printBtn["stat"] = "normal"
            self.startBtn["state"] = "disabled"
            self.infoLabel.config(text="please move waste slide under printer, then hit \" print drop \"")

        def printDrop(self):
            """ print, save position of stage at time of printing """
            def cb():
                self.printLoc = driver.getStageXY()
                self.printBtn["state"] = "disabled"
                self.focusBtn["state"] = "normal"
                self.infoLabel.config(text="please move drop into cross on camera")
            cb() # placeholder for now

            # driver.print()
                # move head down
                # apply voltage 
                # move head up
                
        def dropFocused(self):
            """ get location compute difference, store that in stage, re-enable all GUI buttons"""
            # TODO: also re-enable all other calibration buttons
            focusLoc = driver.getStageXY()
            driver.saveOffset(self.printLoc[0] - focusLoc[0], self.printLoc[1] - focusLoc[0])
            self.startBtn["state"] = "normal"
            self.focusBtn["state"] = "disabled"
            self.infoLabel.configure(text="done! Press start to recalibrate")
            self.abortBtn["state"] = "disabled"
            for btn in self.otherButtons: btn["state"] = "normal"
            print(driver.microscope.stage.printerOffset)

        def abort(self):
            """ wipe self.dropLoc, enable start, disable everything else, including abort"""
            # TODO: also re-enable all other calibration buttons
            self.printLoc = (None, None)

            self.startBtn["state"] = "normal"
            self.printBtn["state"] = "disabled"
            self.focusBtn["state"] = "disabled"
            self.abortBtn["state"] = "disabled"

            self.infoLabel.configure(text="Aborted. Press start to recalibrate")
            for btn in self.otherButtons: btn["state"] = "normal"

class SanityMenu(ttk.Frame):
    def __init__(self, parent):
        ttk.Frame.__init__(self, parent)
        for i in range(3): self.rowconfigure(i, weight=1)
        self.columnconfigure(0, weight=1)
        self.sanity_buttons = []

        overWell = self.OverWell(self, self.sanity_buttons)
        grid(overWell, 0,0,0,0)

        overChannel = self.OverChannel(self, self.sanity_buttons)
        grid(overChannel, 1,0,0,0)

        grabSample = self.GrabSample(self, self.sanity_buttons)
        grid(grabSample,2,0,0,0)
        
    class OverWell(ttk.LabelFrame):
        def __init__(self, parent, buttons):
            ttk.LabelFrame.__init__(self, parent, text="Test head above well")
            for i in range(2): 
                self.rowconfigure(i, weight=1)
                self.columnconfigure(i, weight=1)

            self.sanity_buttons = buttons

            wellLab = ttk.Label(self, text="Select well: (ex: A1)")
            grid(wellLab, 0,0,0,0)

            wellEnt = ttk.Entry(self)
            grid(wellEnt,0,1,0,0)

            goBtn = ttk.Button(self, text="go above well")
            goBtn.grid(row=1,column=0, columnspan=2)

            for child in self.winfo_children(): self.sanity_buttons.append(child)

    class OverChannel(ttk.LabelFrame):
        def __init__(self, parent, buttons):
            ttk.LabelFrame.__init__(self, parent, text="Test head above channel")
            for i in range(2): 
                self.rowconfigure(i, weight=1)
                self.columnconfigure(i, weight=1)

            self.sanity_buttons = buttons

            chanLab = ttk.Label(self, text="Select channel: (ex: 22)")
            grid(chanLab, 0,0,0,0)

            chanEnt = ttk.Entry(self)
            grid(chanEnt,0,1,0,0)

            goBtn = ttk.Button(self, text="go above channel")
            goBtn.grid(row=1,column=0, columnspan=2)

            for child in self.winfo_children(): self.sanity_buttons.append(child)

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
            goBtn.grid(row=1,column=0, columnspan=2)

            for child in self.winfo_children(): self.sanity_buttons.append(child)

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

        grid(FocusChannel(self), 0, 0,0,0)

        showCamBtn = ttk.Button(self, text="open camera display", command=self.openCamera)
        grid(showCamBtn, 1, 0, 0, 0)

        cleanHeadBtn = ttk.Button(self, text="clean the printer head")
        STARTUP_DISABLED_BUTTONS.append(cleanHeadBtn)
        grid(cleanHeadBtn, 2, 0 ,0 ,0)

        showChannelContents = ttk.Button(self, text="show channel contents", command = self.openChannels)
        grid(showChannelContents, 3, 0, 0, 0)

    def openCamera(self):
        def on_closing():
            cameraWin.destroy()
            self.camOpen = False

        if not self.camOpen:
            cameraWin = tk.Toplevel(root)
            cameraWin.title("Camera Display")
            grid(CamWidget(cameraWin), 0,0,0,0)
            cameraWin.protocol("WM_DELETE_WINDOW", on_closing)
            self.camOpen = True

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

class ChannelContents(ttk.Frame):
    def __init__(self, parent):
        ttk.Frame.__init__(self, parent)
        grid(ttk.Label(self, text="this is a placeholder for channel contents popup"), 0 ,0,0,0)
        #TODO: make a good channel contents widget

    
class FocusChannel(ttk.LabelFrame):
    def __init__(self, parent):
        ttk.LabelFrame.__init__(self, parent, text="Show Channel on camera")
        self.rowconfigure(0, weight=1)
        self.columnconfigure(0, weight=1)
        self.columnconfigure(1, weight=1)

        self.chanEnt = ttk.Entry(self)
        STARTUP_DISABLED_BUTTONS.append(self.chanEnt)
        grid(self.chanEnt, 0, 0, 0, 0)

        goBtn = ttk.Button(self, text="focus", command = self.focus)
        STARTUP_DISABLED_BUTTONS.append(goBtn)
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
    
    # TODO: call focus channel in driver
        

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

def close_main():
    def closeCB(): x=3
    
    if driver != None:
        driver.close(closeCB)
        print("driver closed")
    else:
        closeCB()

    root.destroy()

root.protocol("WM_DELETE_WINDOW", close_main)

root.mainloop()
