from multiprocessing.sharedctypes import Value
import tkinter as tk
import sys
sys.path.append("C:/Users/19199/Desktop/automated-sca/src")

from time import sleep
from tkinter import ttk
from threading import Thread
# from gui_widgets.guiCamera import GUICamera
from camera import Camera

from PIL import ImageTk, Image
from tkinter import messagebox
from skimage.transform import resize

class CamWidget(tk.Frame):
    def __init__(self, parent):
        tk.Frame.__init__(self, parent)
        self.s = ttk.Style()
        self.s.configure('red.TButton', foreground='#ff6961')

        self.canvas= tk.Canvas(self, width= 600, height= 400, bg="gray")
        self.canvas.pack()
        self.stopCamThreads = False # flag for ending threads
        self.drawCross = True # whether or not to draw cross on camera
        self.zoomIn = False
        buttonFrame = tk.Frame(self)
        self.cambut = ttk.Button(buttonFrame,text="start camera feed", command = self.camStuffThread, style="Accent.TButton")
        self.cambut.grid(row=0, column=0, padx=5, pady=5)

        self.stopbut = ttk.Button(buttonFrame,text="stop camera feed", command = self.stopcam, style="red.TButton")
        self.stopbut.grid(row=0, column=1, padx=5, pady=5)
        self.stopbut["state"] = "disabled"

        toggleBut = ttk.Button(buttonFrame, text="toggle +", command=self.toggleCross)
        toggleBut.grid(row=0, column=2, padx=5, pady=5)

        zoomBut = ttk.Button(buttonFrame, text="toggle zoom", command=self.toggleZoom)
        zoomBut.grid(row=0, column=3, padx=5, pady=5)

        # gain entry, gain button
        # exposure entry, exposure button
        exposureFrame = ttk.LabelFrame(buttonFrame, text="set exposure (ms)")
        self.expEnt = ttk.Entry(exposureFrame)
        self.expEnt.insert(0, "300")
        expBtn = ttk.Button(exposureFrame, text="set exposure", command=self.setExposure)
        self.expEnt.grid(row = 0, column=0)
        expBtn.grid(row=0, column=1)
        exposureFrame.grid(row=1, column=0)

        gainFrame = ttk.LabelFrame(buttonFrame, text="set gain (brightness factor)")
        self.gainEnt= ttk.Entry(gainFrame)
        self.gainEnt.insert(0, "20")
        gainBtn = ttk.Button(gainFrame, text="set gain", command=self.setGain)
        self.gainEnt.grid(row = 0, column=0)
        gainBtn.grid(row=0, column=1)
        gainFrame.grid(row=1, column=1)

        buttonFrame.pack()

        self.cam = None

    def setGain(self):
        gain = self.gainEnt.get()
        try:
            gain = float(gain)
            if gain < 0.5:
                raise ValueError("gain must be greater than 0.5")

            self.cam.gain = gain
        except Exception as e:
            messagebox.showerror(title="bad gain input", message="Gain must be greater than 0.5")

    def setExposure(self):
        exp = self.expEnt.get()
        try:
            exp = int(exp)
            if (exp < 0):
                raise ValueError("exposure must be >= 1")
            self.cam.setExposure(exp)
        except Exception as e:
            messagebox.showerror(title="bad exposure input", message="please ensure you entered an integer >=1")
            

    def toggleCross(self):
        self.drawCross = not self.drawCross

    def toggleZoom(self):
        self.zoomIn = not self.zoomIn

    def stopcam(self):
        self.stopbut["state"] = "disabled"
        self.cambut["state"] = "normal"
        self.stopCamThreads = True

    def camStuffThread(self):
        self.stopCamThreads = False
        t = Thread(target=self.camStuff)
        t.start()

    def camStuff(self):
        self.cambut["state"] = "disabled"
        try:
            # TODO: revamp this using opencv
            self.cam = Camera() # TODO: maybe construct camera higher up
            # TODO: maybe just do all mmc stuff in this widget??????? (no call to Camera)
            self.stopbut["state"] = "normal"
            while not self.stopCamThreads:
                img = self.cam.getImage(resizeImg=True, crop=self.zoomIn, scale=True)
                # img = self.cam.getImage(resizeImg=False, crop=self.zoomIn, scale=False)
                if self.drawCross:
                    img = self.cam.drawCross(img)
                
                # img = Image.fromarray(img, mode="I;16")
                img = Image.fromarray(img)
                # could have been interrupted after check
                # program seems to run forever if root is closed and we try to run the 2 lines after this if statement
                if self.stopCamThreads: break
            
                imgtk = ImageTk.PhotoImage(image=img)
                self.canvas.create_image(1, 1, anchor="nw", image=imgtk)

            self.cam = None # TODO: maybe have a close function for camera
            print("camera stuff is donezo")
        except Exception as err:
            print(err)
            # TODO: this pops up when camera is closed while feed is live
            # actually, it shouldn't be an error since the camera is gonna be instantiated higher up
            messagebox.showwarning(title="camera error", message="camera failed to load, please check that it's on and that the config file exists")