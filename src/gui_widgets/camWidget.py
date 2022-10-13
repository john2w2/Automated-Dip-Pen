from multiprocessing.sharedctypes import Value
import tkinter as tk
import sys

import cv2
sys.path.append("C:/Users/19199/Desktop/automated-sca/src")

from time import sleep
from tkinter import ttk
from threading import Thread
from camera import Camera

from PIL import ImageTk, Image
from tkinter import messagebox
from skimage.transform import resize

class CamWidget(tk.Frame):
    def __init__(self, parent, camObj):
        # camObj is the instantiated camera to take images from
        tk.Frame.__init__(self, parent)

        self.s = ttk.Style()
        self.s.configure('red.TButton', foreground='#ff6961')

        self.stopCamThreads = True # flag for ending threads
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
        self.expEnt.insert(0, "33")
        expBtn = ttk.Button(exposureFrame, text="set exposure", command=self.setExposure)
        self.expEnt.grid(row = 0, column=0)
        expBtn.grid(row=0, column=1)
        exposureFrame.grid(row=1, column=0)

        # NOTE: due to the speed of the new camera, I think gain is unneeded
        # but we'll see once we plug it into the microscope

        # gainFrame = ttk.LabelFrame(buttonFrame, text="set gain (brightness factor)")
        # self.gainEnt= ttk.Entry(gainFrame)
        # self.gainEnt.insert(0, "20")
        # gainBtn = ttk.Button(gainFrame, text="set gain", command=self.setGain)
        # self.gainEnt.grid(row = 0, column=0)
        # gainBtn.grid(row=0, column=1)
        # gainFrame.grid(row=1, column=1)

        buttonFrame.pack()

        self.cam: Camera = camObj
        self.lose = True

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
            exp = float(exp)
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
        try:
            self.cambut["state"] = "disabled"
            self.stopbut["state"] = "normal"

            self.cam.startAcquisition()

            cv2.namedWindow("feed", cv2.WINDOW_NORMAL)
            cv2.resizeWindow("feed", 601, 401)

            while not self.stopCamThreads and cv2.getWindowProperty('feed', 0) >=0:
                if self.cam.waitingImages() > 0:

                    img = self.cam.getNextFrame()

                    if self.zoomIn: img = self.cam.cropToChannel(img)
                    if self.drawCross: self.cam.drawCross(img, crossColor=2**16-1)
                    # TODO: make gain work???
                    # if self.cam.gain != 1:
                        # img = self.cam.scaleImage(img)
                    
                    cv2.imshow("feed", img)
                if cv2.waitKey(20) >= 0:
                    cv2.destroyAllWindows()
                    break

        except Exception as err:
            print(err)
            # TODO: this pops up when camera is closed while feed is live
            # actually, it shouldn't be an error since the camera is gonna be instantiated higher up
            messagebox.showwarning(title="camera error", message="camera failed to load, please check that it's on and that the config file exists")
        finally:
            cv2.destroyAllWindows()
            self.cam.stopAcquisition()