import tkinter as tk
from tkinter import ttk

# TODO: make this resizable, don't hardcode a plate size
# TODO: make selection color an init parameter so we can make context

class WellSelect(tk.Frame):
    def __init__(self, parent, plateSize=96, bg="#ffffff"):
        tk.Frame.__init__(self, parent)
        self.labels = []
        self.lut = {}
        self.xStart = None
        self.yStart = None
        self.prevSelectedLabels = None
        self.defaultBG = bg

        rows = None
        cols = None
        if plateSize == 6:
            rows = 2
            cols = 3
        elif plateSize == 96:
            rows = 8
            cols = 12
        elif plateSize == 384:
            rows = 16
            cols = 24

        for r in range(rows):
            for c in range(cols):
                name = "abcdefghijklmnopqrstuvwxyz"[r] + str(c + 1)
                lab = tk.Label(self, 
                    name=name, 
                    text=name.upper(),
                    borderwidth=1, 
                    relief="solid", 
                    width=6, 
                    height=3)

                lab.grid(row=r,column=c)
                self.labels.append(lab)

        parent.bind('<1>', self.rectangleSelectClick)
        parent.bind('<3>', self.clearColors)
        parent.bind('<B1-Motion>', self.rectangleSelectDrag)
        parent.bind('<ButtonRelease-1>', self.saveSelectionRect)
        parent.bind('<Key>', self.clearSingle)

    def buildLut(self):
    # build lookup table of labels
    # clear old stuff from lut
        self.lut = {}
        # lut: keys: tuple representing top left, bottom right corners of label, values: reference to label
        # so on drag event, we need to iterate through keys and check if mouse x,y is in the rectangle defined by key
        for label in self.labels:
            rectangle = (label.winfo_rootx(), 
                        label.winfo_rooty(),
                        label.winfo_rootx() + label.winfo_width(),
                        label.winfo_rooty() + label.winfo_height()
                        )
            self.lut[rectangle] =  label

    def dragWell(self, event, toggle=False):
        x,y = event.x_root, event.y_root
        # iterate through labels, check if in rectangle
        for rectangle in self.lut:
            if (self.withinRect(x,y,rectangle)):
                lab = self.lut[rectangle]
                lab.config(background='#80a5e0')
                break # already found the label

    def rectangleSelectClick(self, event):
        # grab top left corner of first click
        self.xStart, self.yStart = event.x_root, event.y_root
        # this is not necessarily the top left point
        # build lookup table 
        self.buildLut()
        self.dragWell(event)

    def rectangleSelectDrag(self, event):
        # select the cells in rectangular fashion
        # selection holds top left and bottom right of selection rectangle
        selection = (min(self.xStart, event.x_root), 
                    min(self.yStart, event.y_root), 
                    max(self.xStart, event.x_root), 
                    max(self.yStart, event.y_root))

        # put everything in selection in selectedRectangles
        selectedLabels = []
        for labRect in self.lut:
            # check if labRect intersects selection
            if (self.rectanglesIntersect(labRect, selection)):
                selectedLabels.append(self.lut[labRect])

        # set all selected to selected color
        for label in selectedLabels:
            label.config(background="#80a5e0")

        if self.prevSelectedLabels != None:
            for label in self.prevSelectedLabels:
                if not label in selectedLabels:
                    label.config(background=self.defaultBG)

        self.prevSelectedLabels = selectedLabels

    def saveSelectionRect(self, event):
        self.prevSelectedLabels = None

    def rectanglesIntersect(self, labRect, selection):
        """ if two rectangles overlap """
        ax1, ay1, ax2, ay2 = selection
        bx1, by1, bx2, by2 = labRect
        # selection bottom above lab top
        if ay2 < by1:
            return False
        # selection top below lab bottom
        if ay1 > by2:
            return False
        # selection right edge left of lab left edge
        if ax2 < bx1:
            return False
        # selection left edge to right of lab right edge
        if ax1 > bx2:
            return False
        return True

    def withinRect(self, x,y,rectangle):
        """ point within a rectangle """
        x1,y1,x2,y2 = rectangle
        return (x >= x1 and x < x2 and y >= y1 and y <y2)

    def clearColors(self, event):
        for label in self.labels:
            label.config(background=self.defaultBG)

    def clearSingle(self, event):
        if (event.keysym == "d"):
            self.buildLut()
            x,y = event.x_root, event.y_root
            for rectangle in self.lut:
                if self.withinRect(x,y, rectangle):
                    label = self.lut[rectangle]
                    label.config(background=self.defaultBG)

    def getSelected(self):
        out = []
        for label in self.labels:
            if label.cget('bg') == "#80a5e0":
                out.append(label.cget("text"))
        # TODO: make this sort better
        # out = sorted(out, key=lambda val: "ABCDEFGHIJKLMNOP".index(val[0]) * 12 + int(val[1:])  )
        return out



