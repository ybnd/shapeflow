import tkinter as tk
import tkinter.ttk as ttk
from collections import namedtuple
from itertools import combinations
from PIL import Image, ImageTk
import numpy as np
import cv2
import os

__coo__ = namedtuple('Coordinate', 'x y')
__ratio__ = 0.4

class ReshapeSelection:
    def __init__(self, canvas, transform):
        self.canvas = canvas
        self.transform = transform

        self.canvas.bind("<Button-1>", self.press)
        self.canvas.bind("<ButtonRelease-1>", self.release)
        self.canvas.master.bind("<Control-z>", self.undo)

        self.initialized = False
        self.has_rectangle = False

        self.lines = []

    def undo(self, event):
        self.initialized = False
        self.has_rectangle = False
        for button in self.corners: button.delete()
        for line in self.lines: self.canvas.delete(line)


    def press(self, event):

        if not self.initialized:
            self.start = __coo__(x = event.x, y = event.y)
            self.initialized = True

    def release(self, event):
        if not self.has_rectangle:
            self.stop = __coo__(x=event.x, y=event.y)

            self.coordinates = [
                __coo__(self.start.x, self.start.y), # todo: this thing practically begs to be done in a short, sweet, sugary way!
                __coo__(self.start.x, self.stop.y),
                __coo__(self.stop.x, self.stop.y),
                __coo__(self.stop.x, self.start.y)
            ]

            self.corners = []

            for coordinate in self.coordinates:
                self.corners.append(
                    Corner(self, coordinate)
                )

            self.has_rectangle = True
            self.update()

    def update(self):
        self.redraw()
        co = [corner.co for corner in self.corners]
        # print(f"Coordinates: {co}")
        self.transform.update(co)

    def redraw(self):
        for line in self.lines:
            self.canvas.delete(line)

        for i, corner in enumerate(self.corners):
            self.lines.append(self.canvas.create_line(self.corners[i-1].co, corner.co))

        for corner in self.corners:
            self.canvas.lift(corner)

class Corner:
    __side__ = 35
    handle = None
    alpha = 0.05

    def __init__(self, selection, co, r = None):
        if r is None:
            r = self.__side__

        self.canvas = selection.canvas
        self.selection = selection
        self.co = co
        # self.id = self.canvas.create_oval(co.x-r, co.y-r, co.x+r, co.y+r, fill = 'LightGray')
        if self.handle is None:
            pim = Image.new('RGBA', (self.__side__, self.__side__), (255, 0, 0, int(self.alpha * 255)))
            self.handle = ImageTk.PhotoImage(image=pim)

        self.id = self.canvas.create_image(co.x, co.y, image = self.handle, anchor ='center')

        self.canvas.tag_bind(self.id, "<ButtonPress-1>", self.press)
        self.canvas.tag_bind(self.id, "<ButtonRelease-1>", self.release)
        self.canvas.tag_bind(self.id, "<Enter>", self.enter)
        self.canvas.tag_bind(self.id, "<Leave>", self.leave)

        self.dragging = False

    def press(self, event):
        self.previous = __coo__(event.x, event.y)
        self.drag_binding = self.canvas.bind("<Motion>", self.drag)
        self.dragging = True

    def drag(self, event):
        self.canvas.move(self.id, event.x - self.previous.x, event.y - self.previous.y)
        co = self.canvas.coords(self.id)
        self.co = __coo__(co[0], co[1])
        # self.co = __coo__((co[0] + co[2]) / 2, (co[1] + co[3]) / 2)
        self.selection.redraw()
        self.previous = self.co


    def release(self, event):
        self.canvas.unbind("<Motion>", self.drag_binding)
        co = self.canvas.coords(self.id)
        self.co = __coo__(co[0], co[1])
        # self.co = __coo__((co[0]+co[2])/2, (co[1]+co[3])/2)
        self.selection.update()
        self.leave(event)
        self.dragging = False

    def delete(self):
        self.canvas.delete(self.id)

    def enter(self, event):
        self.canvas.configure(cursor = 'hand2')

    def leave(self, event):
        if not self.dragging:
            self.canvas.configure(cursor = 'left_ptr')

class ImageDisplay:
    __ratio__ = __ratio__
    def __init__(self, window, image: np.ndarray, overlay: np.ndarray):
        self.window = window # todo: some of this should actually be in an 'app' or 'window' object
        self.shape = image.shape
        self.canvas = tk.Canvas(
            self.window,
            width = int(self.shape[1]*self.__ratio__) + 500,
            height = int(self.shape[0]*self.__ratio__)
        )
        self.canvas.pack()
        self.scaled_shape = (int(self.shape[1]*self.__ratio__), int(self.shape[0]*self.__ratio__))

        self.image = image
        height, width, channels = image.shape
        img = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        img = Image.fromarray(img)
        img.thumbnail((int(width * self.__ratio__), int(height * self.__ratio__)))
        img = ImageTk.PhotoImage(image=img)
        self.canvas.create_image(0, 0, image=img, anchor=tk.NW) # todo: image disappears for some reason?

        self.transform = TransformOverlay(self.canvas, self.image, overlay, self.scaled_shape)
        self.selection = ReshapeSelection(self.canvas, self.transform)

        self.canvas.mainloop()

class TransformImage:
    def __init(self, window):
        self.window = window

class TransformOverlay:
    coordinates = np.float32([[200,200],[300,200],[200,300],[300,300]]) # todo: this should be ~ the shape of the overlay
    __ratio__ =__ratio__
    alpha = 0.1

    def __init__(self, canvas, image, overlay_img, co):
        self.overlay = overlay_img
        self.original = image
        self.image = None
        self.canvas = canvas

        shape = self.overlay.shape

        self.co = co
        self.height = co[1]
        self.width = int(shape[0] * co[1] / shape[1])

        self.to_coordinates = np.array( # selection rectangle: bottom left to top right
            [
                [0, shape[0]], [0, 0], [shape[1], 0], [shape[1], shape[0]]
            ]
        )

    def update(self, from_coordinates):
        self.transform = cv2.getPerspectiveTransform(np.float32(from_coordinates)/self.__ratio__, np.float32(self.to_coordinates))
        Y,X,C = self.overlay.shape
        self.image = cv2.warpPerspective(self.original, self.transform, (X,Y))

        cv2.addWeighted(self.overlay, self.alpha, self.image, 1-self.alpha, 0, self.image)

        height, width, channels = self.overlay.shape
        img = cv2.cvtColor(self.image, cv2.COLOR_BGR2RGB)
        img = Image.fromarray(img)
        img.save('img.bmp')
        img.thumbnail((int(width * self.__ratio__), int(height * self.__ratio__)))
        self.img = ImageTk.PhotoImage(image=img)
        self.canvas.create_image(self.co[0], 0, image=self.img, anchor=tk.NW)

        print(f"The transform from {from_coordinates} to {self.to_coordinates} is {self.transform}")

window = tk.Tk()

cap = cv2.VideoCapture(os.path.join(os.getcwd(), "video.mp4"))

frameN = cap.get(cv2.CAP_PROP_FRAME_COUNT)

cap.set(cv2.CAP_PROP_POS_FRAMES, int(frameN/4))
ret, frame = cap.read()

overlay = cv2.imread(os.path.join(os.getcwd(), "overlay2.png"))

rect = ImageDisplay(window, frame, overlay)
# window.mainloop()
