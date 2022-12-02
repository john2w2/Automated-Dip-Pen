from math import ceil
from multiprocessing.sharedctypes import Value
import tkinter as tk
import sys
from utils.camera_utils import *

import cv2
sys.path.append("C:/Users/19199/Desktop/automated-sca/src")

from time import sleep
from tkinter import ttk
from threading import Thread
from orcaFlash import OrcaFlashV2

from PIL import ImageTk, Image
from tkinter import messagebox
from skimage.transform import resize

class CamWidget(tk.Frame):
    def __init__(self, parent, camObj: OrcaFlashV2):
        # camObj is the instantiated camera to take images from
        tk.Frame.__init__(self, parent)

        self.s = ttk.Style()
        self.s.configure('red.TButton', foreground='#ff6961')

        self.stopCamThreads = True # flag for ending threads
        self.drawCross = True # whether or not to draw cross on camera
        self.zoomIn = False
        self.zoomAmount = 0 # a value from 0 to 90
        
        buttonFrame = tk.Frame(self)
        self.cambut = ttk.Button(buttonFrame,text="start camera feed", command = self.camStuffThread, style="Accent.TButton")
        self.cambut.grid(row=0, column=0, padx=5, pady=5)

        self.stopbut = ttk.Button(buttonFrame,text="stop camera feed", command = self.stopcam, style="red.TButton")
        self.stopbut.grid(row=0, column=1, padx=5, pady=5)
        self.stopbut["state"] = "disabled"

        toggleBut = ttk.Button(buttonFrame, text="toggle +", command=self.toggleCross)
        toggleBut.grid(row=0, column=2, padx=5, pady=5)

        # zoomBut = ttk.Button(buttonFrame, text="toggle zoom on channel", command=self.toggleZoom)
        # zoomBut.grid(row=0, column=3, padx=5, pady=5)

        zoomInBut = ttk.Button(buttonFrame, text="zoom in", command=self.incZoom)
        zoomInBut.grid(row=0, column=4, padx=5, pady=5)

        zoomOutBut = ttk.Button(buttonFrame, text="zoom out", command=self.decZoom)
        zoomOutBut.grid(row=0, column=5, padx=5, pady=5)

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

        gainFrame = ttk.LabelFrame(buttonFrame, text="set gain (brightness factor)")
        self.gainEnt= ttk.Entry(gainFrame)
        self.gainEnt.insert(0, "20")
        gainBtn = ttk.Button(gainFrame, text="set gain", command=self.setGain)
        self.gainEnt.grid(row = 0, column=0)
        gainBtn.grid(row=0, column=1)
        gainFrame.grid(row=1, column=1)

        saveBtn = ttk.Button(buttonFrame, text="save image as tiff", command=self.saveImage)
        saveBtn.grid(row=1, column=2)


        buttonFrame.pack()


        self.cam: OrcaFlashV2 = camObj
        self.lose = True
        self.gain: int = 1

    def saveImage(self):
        try:
            save_image_from_camera(self.cam, self.gain)
        except:
            print("failed to save, probably not acquiring")

    def incZoom(self):
        if self.zoomAmount < 90:
            self.zoomAmount += 10
        elif self.zoomAmount < 95:
            self.zoomAmount += 5

    def decZoom(self):
        if self.zoomAmount == 95:
            self.zoomAmount -= 5
        elif self.zoomAmount > 0:
            self.zoomAmount -= 10

    def setGain(self):
        gain = self.gainEnt.get()
        try:
            gain = int(gain)
            if gain < 1:
                raise ValueError("gain must be at least than 1")

            self.gain = gain
        except Exception as e:
            messagebox.showerror(title="bad gain input", message="Gain must be greater than 0.5")

    def setExposure(self):
        exp = self.expEnt.get()
        try:
            exp = float(exp)
            if (exp < 0):
                raise ValueError("exposure must be >= 1")
            self.cam.set_exposure(exp)
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

            self.cam.connect()

            self.cam.start_acquisition()

            cv2.namedWindow("feed", cv2.WINDOW_KEEPRATIO)
            cv2.resizeWindow("feed", 600, 600)

            while not self.stopCamThreads and cv2.getWindowProperty('feed', 0) >=0:
                if self.cam.get_num_waiting_frames() > 0:

                    img = self.cam.get_next_frame()
                    img = zoom_by_percentage(img, self.zoomAmount)
                    if self.drawCross: draw_cross(img, 
                        crossColor=2**16-1,
                        crossWidth= ceil(((100 - self.zoomAmount) / 100) * 5)   
                        )
                    apply_gain(img, self.gain)
                    imageRect = cv2.getWindowImageRect("feed")

                    # if user resizes window into non-square
                    # make the frame square again
                    if (imageRect[2] != imageRect[3]):
                        minRes = min(imageRect[2], imageRect[3])
                        cv2.resizeWindow("feed", minRes, minRes)

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
            self.cam.stop_acquisition()
            self.cam.reset()