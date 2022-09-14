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
        buttonFrame = tk.Frame(self)
        self.cambut = ttk.Button(buttonFrame,text="start camera feed", command = self.camStuffThread, style="Accent.TButton")
        self.cambut.grid(row=0, column=0, padx=5, pady=5)

        self.stopbut = ttk.Button(buttonFrame,text="stop camera feed", command = self.stopcam, style="red.TButton")
        self.stopbut.grid(row=0, column=1, padx=5, pady=5)
        self.stopbut["state"] = "disabled"

        toggleBut = ttk.Button(buttonFrame, text="toggle +", command=self.toggleCross)
        toggleBut.grid(row=0, column=2, padx=5, pady=5)

        buttonFrame.pack()

    def toggleCross(self):
        self.drawCross = not self.drawCross

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
            cam = Camera()
            self.stopbut["state"] = "normal"
            while not self.stopCamThreads:
                img = cam.getImage()
                img = resize(img, (401, 601), preserve_range=True)
                if self.drawCross:
                    img = cam.drawCross(img)
                img = Image.fromarray(img)
                # could have been interrupted after check
                # program seems to run forever if root is closed and we try to run the 2 lines after this if statement
                if self.stopCamThreads: break
                imgtk = ImageTk.PhotoImage(image=img)
                self.canvas.create_image(1, 1, anchor="nw", image=imgtk)
            del cam # TODO: maybe have a close function for camera
            print("camera stuff is donezo")
        except Exception as err:
            print(err)
            messagebox.showwarning(title="camera error", message="camera failed to load, please check that it's on and the config file")