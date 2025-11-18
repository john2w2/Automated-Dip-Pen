import tkinter as tk
import sys

from tkinter import ttk
from tkinter import messagebox
sys.path.append("C:\\Users\\NikonTE300CE\\Desktop\\automated-sca\\src")
from arm import Arm
from threading import Thread


root = tk.Tk()
root.title("arm controller menu")

arm: Arm = None

def connect():
    global arm
    try:
        arm = Arm(arduinoPort="COM5")
        startBtn["state"] = "disabled"
        calibBtn["state"] = "normal"
    except:
        messagebox.showerror(title="connection error", message="please make sure the usb is plugged into the arduino and that it is not being controlled by any other software")

def moveMM():
    global arm
    ent = moveEnt.get()
    try:
        ent = int(ent)
        arm.zmotor.moveToZRelInMM(ent)
    except:
        messagebox.showerror(title="invalid input", message="please make sure you entered an integer")

def calibrate():
    global arm
    arm.calibrateOrigin()
    moveEnt["state"] = "normal"
    moveBut["state"] = "normal"

startBtn = ttk.Button(root, text="connect to arduino", command=connect)
startBtn.pack()

calibBtn = ttk.Button(root, text="calibrate arm (must be run after connecting)", command=calibrate)
calibBtn.pack()
calibBtn["state"] = "disabled"

moveContainer = ttk.LabelFrame(root, text="Move in MM (< 0 is down, > 0 is up)")
moveEnt = ttk.Entry(moveContainer)
moveBut = ttk.Button(moveContainer, text="move", command=moveMM)
moveContainer.pack()
moveEnt.pack()
moveBut.pack()
moveEnt["state"] = "disabled"
moveBut["state"] = "disabled"




def on_closing():
    if arm != None:
        arm.close()
    root.destroy()

root.protocol("WM_DELETE_WINDOW", on_closing)
root.mainloop()