import tkinter as tk
from tkinter import ttk

class ChannelWidget(tk.Frame):
    """
    
    """
    def __init__(self, parent):
        tk.Frame.__init__(self, parent)
        self.contents = ["empty" for _ in range(100)]

        canvas = tk.Canvas(self)
        scrollbar = ttk.Scrollbar(self, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)

        style = ttk.Style()
        style.theme_use('clam')
        style.configure("Horizontal.TScrollbar", gripcount=0,
                        background="Green", darkcolor="DarkGreen", lightcolor="LightGreen",
                        troughcolor="gray", bordercolor="blue", arrowcolor="white")

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(
                scrollregion=canvas.bbox("all")
            )
        )

        def withinRect(x, y, rectangle):
            """ point within a rectangle """
            x1,y1,x2,y2 = rectangle
            return (x >= x1 and x < x2 and y >= y1 and y <y2)

        def _on_mousewheel(event):
            x1, y1 = canvas.winfo_rootx(), canvas.winfo_rooty()
            x2, y2 = x1 + canvas.winfo_width(), y1 + canvas.winfo_height()
            rectangle = (x1, y1, x2, y2)
            if withinRect(event.x_root, event.y_root, rectangle):
                canvas.yview_scroll(int(-1*(event.delta/120)), "units")


        canvas.bind_all("<MouseWheel>", _on_mousewheel)
        canvas.create_window((0, 0), window=scrollable_frame)
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.grid_columnconfigure(0,weight=1)

        self.labels = []
        for i in range(100):
            lab = ttk.Label(scrollable_frame, 
                            text=str(i + 1) + "  -    -   " + self.contents[i],
                            borderwidth=2,
                            relief="ridge",
                            width=62,
                            background="gray"
                            )
            lab.pack(expand=True, fill="x", anchor="w")
            self.labels.append(lab)
            lab.bind("<Button-1>", lambda event:print(lab.cget("text")))

        self.config(borderwidth=1, relief="solid")
        scrollbar.pack(side="left", fill="y")
        canvas.pack(side="left")

    def updateContents(self, contents):
        self.contents = contents
        for index, lab in enumerate(self.labels):
            lab.config(text=str(index) + "  -    -   " + self.contents[index],
                        background="gray" if self.contents[index] == "empty" else "white"
            )