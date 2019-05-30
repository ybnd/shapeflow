import sys
import time
import tkinter as tk
import tkinter.messagebox
from collections import namedtuple

import cv2
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import screeninfo
from PIL import Image, ImageTk
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.figure import Figure

import isimple.video.metadata as metadata

__monitor_w__ = min(m.width for m in screeninfo.get_monitors())
__monitor_h__ = min(m.height for m in screeninfo.get_monitors())

__coo__ = namedtuple('Coordinate', 'x y')
__ratio__ = 0.6


def rotations(sequence) -> list:  # todo: clean up
    """ Returns all rotations of a list. """

    def rotate(seq, n: int) -> list:
        return seq[n:] + seq[:n]

    rotation_list = []
    for N in range(len(sequence)):
        rotation_list.append(rotate(sequence, N))

    return rotation_list


class ScriptWindow(tk.Tk):
    def __init__(self):
        self.done = False
        tk.Tk.__init__(self)
        self.protocol("WM_DELETE_WINDOW", self.close)

    def focus(self):
        self.focus_force()

    def close(self, do_exit=True):
        """ Called when user tries to close the window. """
        if self.done:
            # Finished!
            self.destroy()
            if do_exit:
                sys.exit()
                # todo: this is a temporary solution...
                #  why doesn't self.destroy() "let the mainloop go?"
                #  -> maybe a mainloop is created elsewhere also?...
        else:
            # Not finished yet!
            if tkinter.messagebox.askokcancel("Quit", "The script is still running. Really quit?"):
                self.destroy()
                if do_exit:
                    sys.exit()


class ReshapeSelection:
    """
        Reshape-able rectangle ROI selection for tkinter canvases
    """

    def __init__(self, window, transform, initial_coordinates=None):
        self.imagedisplay = window
        self.window = window.window  # todo: confusing!!!
        self.canvas = window.canvas
        self.transform = transform  # transform matrix object

        self.canvas.bind("<Button-1>", self.press)
        self.canvas.bind("<ButtonRelease-1>", self.release)
        self.canvas.master.bind("<Control-z>", self.undo)
        self.canvas.master.bind("<Escape>", self.quit)

        self.initialized = False
        self.has_rectangle = False

        self.lines = []
        self.start = None
        self.stop = None
        self.corners = None
        self.coordinates = initial_coordinates

        self.order = self.transform.order
        self.initialize()

    def initialize(self):
        if self.coordinates is not None:
            self.get_corners()

    def undo(self, _):
        """ Callback to clear selection rectangle """
        self.initialized = False
        self.has_rectangle = False
        for button in self.corners:
            button.delete()
        for line in self.lines:
            self.canvas.delete(line)

    def press(self, event):
        """ Mouse press callback. Initializes rectangle dragging. """
        if not self.initialized:
            self.start = __coo__(x=event.x, y=event.y)
            self.initialized = True

    def release(self, event):
        """ Mouse release callback. Commits rectangle dragging result. """
        if not self.has_rectangle:
            self.stop = __coo__(x=event.x, y=event.y)

            # Get coordinates of rectangle corners
            self.coordinates = [
                __coo__(self.start.x, self.start.y),  # Bottom Left
                __coo__(self.start.x, self.stop.y),  # ?      ?
                __coo__(self.stop.x, self.stop.y),  # ?      ?
                __coo__(self.stop.x, self.start.y)  # Top    Right
            ]

            self.get_corners()

    def get_corners(self):
        self.corners = []
        names = ['BL', '?1', '?2', 'TR']

        # Initialize corner objects
        for i, coordinate in enumerate(self.coordinates):
            self.corners.append(
                Corner(self, coordinate, name=names[i])
            )

        self.has_rectangle = True
        self.update()

    def update(self):
        """ Update selection rectangle and transform matrix. """
        self.redraw()
        co = [corner.co for corner in self.corners]

        # Permute the coordinate list
        co = [co[i] for i in self.order]

        # print(f"Coordinates: {co}")
        self.transform.get_new_transform(co, self.order)

    def redraw(self):
        """ Redraw selection rectangle on the canvas. """
        for line in self.lines:
            self.canvas.delete(line)

        for i, corner in enumerate(self.corners):
            self.lines.append(self.canvas.create_line(self.corners[i - 1].co, corner.co))

        for corner in self.corners:
            self.canvas.focus(corner)

    def quit(self, _):
        """ Close the window. """
        self.canvas.master.destroy()


class Corner:
    """
        Draggable corner for ROI selection rectangle
    """

    __side__ = 35
    __fontsize__ = 12
    handle = None
    alpha = 0.05

    def __init__(self, selection, co, name=''):
        self.canvas = selection.canvas
        self.selection = selection
        self.co = co
        # self.id = self.canvas.create_oval(co.x-r, co.y-r, co.x+r, co.y+r, fill = 'LightGray')
        self.name = name

        self.previous = None
        self.drag_binding = None

        if self.handle is None:
            pim = Image.new('RGBA', (self.__side__, self.__side__), (255, 0, 0, int(self.alpha * 255)))

            self.handle = ImageTk.PhotoImage(image=pim)

            # self.label = tk.Label(
            #     self.selection.window, image=self.handle, text=self.name,
            #     compound=tk.CENTER
            # )
            # self.label.place(x = co.x, y = co.y)
        if isinstance(co, __coo__):
            self.id = self.canvas.create_image(co.x, co.y, image=self.handle, anchor='center')
        else:
            self.id = self.canvas.create_image(co[0], co[1], image=self.handle, anchor='center')

        self.canvas.tag_bind(self.id, "<ButtonPress-1>", self.press)
        self.canvas.tag_bind(self.id, "<ButtonRelease-1>", self.release)
        self.canvas.tag_bind(self.id, "<Enter>", self.enter)
        self.canvas.tag_bind(self.id, "<Leave>", self.leave)

        self.dragging = False

    def press(self, event):
        """ Callback for mouse click """
        self.previous = __coo__(event.x, event.y)
        self.drag_binding = self.canvas.bind("<Motion>", self.drag)
        self.dragging = True

    def drag(self, event):
        """ Callback for mouse movement after click """
        self.canvas.move(
            self.id, event.x - self.previous.x, event.y - self.previous.y
        )
        co = self.canvas.coords(self.id)
        self.co = __coo__(co[0], co[1])
        # self.co = __coo__((co[0] + co[2]) / 2, (co[1] + co[3]) / 2)
        self.selection.update()
        self.previous = self.co

    def release(self, event):
        """ Callback for mouse release """
        self.canvas.unbind("<Motion>", self.drag_binding)
        co = self.canvas.coords(self.id)
        self.co = __coo__(co[0], co[1])
        # self.co = __coo__((co[0]+co[2])/2, (co[1]+co[3])/2)
        self.selection.update()
        self.leave(event)
        self.dragging = False

    def delete(self):
        self.canvas.delete(self.id)

    def enter(self, _):
        """ Callback - mouse is hovering over object """
        self.canvas.configure(cursor='hand2')

    def leave(self, _):
        """ Callback - mouse is not hovering over object anymore """
        if not self.dragging:
            self.canvas.configure(cursor='left_ptr')


class ImageDisplay:
    """
        OpenCV image display in tkinter canvas with link to ROI selection and coordinate transform.
    """
    __ratio__ = __ratio__ * __monitor_w__
    __rotations__ = {str(p): p for p in rotations(list(range(4)))}

    def __init__(self, window: ScriptWindow, image: np.ndarray, overlay: np.ndarray, transform: np.ndarray,
                 order: set = (0, 1, 2, 3), initial_coordinates=None):
        self.window = window  # todo: some of this should actually be in an 'app' or 'window' object
        self.shape = image.shape

        self.__ratio__ = self.__ratio__ / self.shape[1]

        self.__width__ = int(self.shape[1] * self.__ratio__) + overlay.shape[1] * self.__ratio__

        if self.__width__ >= __monitor_w__:
            self.__width__ = __monitor_w__ * 0.98
            self.__ratio__ = self.__width__ / (self.shape[1] + overlay.shape[1])

        self.canvas = tk.Canvas(
            self.window,
            width=self.__width__,
            height=max(int(self.shape[0] * self.__ratio__), int(overlay.shape[0] * self.__ratio__))
        )
        self.canvas.pack()
        self.scaled_shape = (int(self.shape[1] * self.__ratio__), int(self.shape[0] * self.__ratio__))

        self.original = image
        height, width, channels = image.shape
        img = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        img = Image.fromarray(img)
        img.thumbnail((int(width * self.__ratio__), int(height * self.__ratio__)))
        self.display_image = img
        self.tkimage = ImageTk.PhotoImage(image=img)
        self.canvas.create_image(0, 0, image=self.tkimage, anchor=tk.NW)

        self.transform = TransformImage(
            self.canvas,
            image,
            overlay,
            self.scaled_shape,
            self.window.transform_callback,
            self.__ratio__,
            transform,
            order
        )
        self.selection = ReshapeSelection(
            self,
            self.transform,
            initial_coordinates,
        )

        self.order = order
        self.rotation = tk.StringVar(self.canvas.master)
        self.option = tk.OptionMenu(
            self.canvas.master,
            self.rotation,
            *set(self.__rotations__.keys()),
            command=self.permute
        )
        self.rotation.set(str(self.order))
        self.option.pack()

        self.window.focus()
        self.canvas.mainloop()

    def permute(self, permutation_id):
        self.selection.order = self.__rotations__[permutation_id]
        self.selection.update()


class TransformImage:
    """
        OpenCV perspective transform, overlay alpha blending and display with tkinter
    """
    alpha = 0.1

    def __init__(self, canvas, image, overlay_img, co, callback, ratio, initial_transform, initial_order=(0, 1, 2, 3)):
        self.overlay = overlay_img
        self.original = image
        self.image = None
        self.img = None  # todo: image and img :)
        self.canvas = canvas
        self.callback = callback
        self.__ratio__ = ratio

        shape = self.overlay.shape

        self.co = co
        self.height = co[1]
        self.width = int(shape[0] * co[1] / shape[1])

        self.to_coordinates = np.array(  # selection rectangle: bottom left to top right
            [
                [0, shape[0]], [0, 0], [shape[1], 0], [shape[1], shape[0]]
            ]
        )

        self.transform = initial_transform
        self.order = initial_order
        self.show_overlay()

        if np.array_equal(self.transform, np.eye(3)):
            self.update()

    def get_new_transform(self, from_coordinates, order):  # todo: don't need order here?
        """ Recalculate transform and show overlay. """
        self.transform = cv2.getPerspectiveTransform(
            np.float32(from_coordinates) / self.__ratio__,
            np.float32(self.to_coordinates)
        )

        # Round to remove unnecessary precision
        # self.transform = np.around(self.transform, decimals=3)

        # pret = cv2.warpPerspective(self.original, self.pre_transform, (X0,Y0))

        self.update()
        self.callback(self.transform, from_coordinates)

    def update(self):
        """ Update image based  """  # todo: transformed + overlay should be a VideoAnalyzer method
        y, x, c = self.overlay.shape
        self.image = cv2.warpPerspective(self.original, self.transform, (x, y))

        cv2.addWeighted(self.overlay, self.alpha, self.image, 1 - self.alpha, 0, self.image)

        height, width, channels = self.overlay.shape
        img = cv2.cvtColor(self.image, cv2.COLOR_BGR2RGB)
        img = Image.fromarray(img)
        img.thumbnail((int(width * self.__ratio__), int(height * self.__ratio__)))
        self.img = ImageTk.PhotoImage(image=img)
        self.canvas.create_image(self.co[0], 0, image=self.img, anchor=tk.NW)

        # self.callback(self.transform)

    def show_overlay(self):
        """ Show overlay """
        height, width, channels = self.overlay.shape
        img = cv2.cvtColor(self.overlay, cv2.COLOR_BGR2RGB)
        img = Image.fromarray(img)
        img.thumbnail((int(width * self.__ratio__), int(height * self.__ratio__)))
        img = ImageTk.PhotoImage(image=img)
        self.canvas.create_image(self.co[0], 0, image=img, anchor=tk.NW)


def hsvimg2tk(image, ratio=1.0):
    """ Convert OpenCV HSV image to PhotoImage object """
    img = cv2.cvtColor(image, cv2.COLOR_HSV2RGB)
    shape = img.shape
    img = Image.fromarray(img)
    img.thumbnail(
        (int(shape[1] * ratio), int(shape[0] * ratio))
    )
    img = ImageTk.PhotoImage(image=img)
    return img


def binimg2tk(image, ratio=1.0):
    """ Convert OpenCV binary image to PhotoImage object """
    img = cv2.cvtColor(image, cv2.COLOR_GRAY2RGB)
    shape = img.shape
    img = Image.fromarray(img)
    img.thumbnail(
        (int(shape[1] * ratio), int(shape[0] * ratio))
    )
    img = ImageTk.PhotoImage(image=img)
    return img


class ColorPicker:
    """
        Select colours by clicking image pixels.
    """
    __w_spacing__ = 3
    __h_scale__ = 25

    def __init__(self, window, mask, video):
        self.window = window
        self.mask = mask
        self.video = video

        self.coo = None

        image = self.mask.mask(self.video.get_frame(1))

        self.im_masked = None
        self.im_filtered = None

        self.__width__ = image.shape[1] * 2 + self.__w_spacing__,

        if isinstance(self.__width__, tuple):
            self.__width__ = self.__width__[0]

        if self.__width__ >= __monitor_w__:
            self.__width__ = __monitor_w__ * 0.98
            self.__ratio__ = self.__width__ / (image.shape[1] * 2 + self.__w_spacing__)
        else:
            self.__ratio__ = 1

        self.canvas = tk.Canvas(
            self.window,
            width=self.__width__,
            height=image.shape[0]
        )
        self.slider = tk.Scale(
            self.window,
            from_=1,
            to=self.video.frameN,
            orient=tk.HORIZONTAL,
            command=self.track,
            length=self.__width__,
            width=self.__h_scale__
        )
        self.canvas.pack()
        self.slider.pack()

        self.center = self.__width__ / 2.0

        self.canvas.bind("<Button-1>", self.pick)
        self.canvas.master.bind("<Escape>", self.quit)

        self.update()
        self.window.focus()
        self.canvas.mainloop()

    def update(self):
        """ Update UI """
        masked, filtered = self.mask.get_images()

        self.im_masked = hsvimg2tk(masked, ratio=self.__ratio__)
        self.im_filtered = binimg2tk(filtered, ratio=self.__ratio__)

        self.canvas.create_image(
            0, 0,
            image=self.im_masked, anchor=tk.NW
        )
        self.canvas.create_image(
            self.center + self.__w_spacing__, 0,
            image=self.im_filtered, anchor=tk.NW
        )

        self.window.selection_callback(
            {metadata.__from__: self.mask.filter_from, metadata.__to__: self.mask.filter_to}
        )

    def pick(self, event):
        """ Pick a colour """
        self.coo = __coo__(x=event.x, y=event.y)
        self.mask.pick(self.coo)
        self.update()

    def track(self, value):
        """ Scrollbar callback - track through the video. """
        self.mask.track(int(value))
        self.update()

    def quit(self, _):
        """ Close the window. """
        self.window.destroy()


class OverlayAlignWindow(ScriptWindow):
    __default_frame__ = 0.5
    __title__ = "Overlay alignment"

    def __init__(self, video):
        ScriptWindow.__init__(self)
        self.data = video
        self.title(self.data.name)

        self.image = ImageDisplay(
            self,
            self.data.get_frame_at(self.__default_frame__, do_warp=False, to_hsv=False),
            self.data.overlay,
            self.data.transform,
            self.data.order,
            self.data.coordinates,
        )

    def transform_callback(self, transform, coordinates):
        self.data.transform = transform
        self.data.coordinates = coordinates
        self.done = True


class MaskFilterWindow(ScriptWindow):
    __title__ = 'Filter hue selection'

    def __init__(self, mask):
        ScriptWindow.__init__(self)
        self.data = mask
        self.title(self.data.name)

        self.picker = ColorPicker(
            self,
            mask=mask,
            video=mask.video
        )

    def selection_callback(self, selection):  # todo: don't need selection here?
        self.done = True


class ProgressWindow(ScriptWindow):
    __ratio__ = 0.25
    __plot_pad__ = 0.075
    __pad__ = 2
    __dpi__ = 100

    __title__ = 'Volume measurement'

    def __init__(self, video):
        ScriptWindow.__init__(self)
        self.video = video
        self.title(self.video.name)

        self.canvas_height = self.__ratio__ * __monitor_h__
        self.__raw_width__ = self.video.raw_frame.shape[1] * \
            self.canvas_height / self.video.raw_frame.shape[0]
        self.__processed__ = self.video.frame.shape[1] * \
            self.canvas_height / self.video.frame.shape[0]

        self.tmax = self.video.frameN / self.video.fps
        self.t0 = time.time()

        frame = self.video.get_frame(1)
        self.img = None
        self.df = None
        self.t = None
        self.size = frame.shape

        self.canvas_width = self.__raw_width__ + self.__processed__ + self.__pad__

        self.canvas = tk.Canvas(
            self,
            width=self.canvas_width,
            height=self.canvas_height
        )
        self.update_image()
        self.canvas.pack()

        figw = self.canvas_width / self.__dpi__

        plt.ioff()
        self.fig = Figure(
            figsize=(figw, 6 / 9 * figw), dpi=self.__dpi__
        )
        self.ax = self.fig.add_subplot(111)
        plt.tight_layout(pad=0)
        self.fig.subplots_adjust(
            left=self.__plot_pad__, bottom=self.__plot_pad__,
            right=1 - self.__plot_pad__ / 2, top=1 - self.__plot_pad__
        )

        self.figcanvas = FigureCanvasTkAgg(self.fig, master=self)
        self.figcanvas.draw()

        self.toolbar = NavigationToolbar2Tk(self.figcanvas, window=self)
        self.toolbar.update()
        self.figcanvas.get_tk_widget().pack(side=tk.BOTTOM, fill=tk.BOTH, expand=1)

        self.figcanvas.get_tk_widget().pack()

    def update_image(self):
        """ Show the current video frame in the UI """
        if self.video.frame is not None:
            self.img = hsvimg2tk(
                self.video.raw_frame, ratio=self.canvas_height / self.video.raw_frame.shape[0]
            )
            self.state = hsvimg2tk(
                self.video.get_state_image(), ratio=self.canvas_height / self.video.frame.shape[0]
            )
            self.canvas.create_image(
                0, 0, image=self.img, anchor=tk.NW
            )
            self.canvas.create_image(
                self.__raw_width__ + self.__pad__, 1,
                image=self.state, anchor=tk.NW
            )

    def update(self):
        self.update_image()

        self.figcanvas.draw()
        ScriptWindow.update(self)

    def plot(self, t, areas):  # todo: this should call a method in isimple.video.visualization
        """ Update the plot. """
        if areas is not None:
            try:
                self.t = t
                elapsed = time.time() - self.t0

                areas = np.transpose(areas) / (self.video.__overlay_DPI__ / 25.4) ** 2 * self.video.h
                # todo: do this at the VideoAnalyzer level!

                self.ax.clear()
                for i, curve in enumerate(areas):
                    color = cv2.cvtColor(
                        np.array([[np.array(self.video.plot_colors[self.video.masks[i]], dtype=np.uint8)]]),
                        cv2.COLOR_HSV2RGB
                    )[0, 0] / 255
                    # todo: shouldn't need to do this calculation at every time step!
                    self.ax.plot(
                        t, curve,
                        label=self.video.masks[i].name,
                        color=tuple(color),
                        linewidth=2
                    )

                # todo: is it necessary to re-do all of the plot legend/axis stuff for every time step?
                self.ax.legend(loc='center right')
                self.ax.set_title(
                    f"{t[-1] / self.tmax * 100:.0f}%  ({elapsed:.0f} s elapsed "
                    f" @ {t[-1] / elapsed:.1f} x)", size=18, weight='bold'
                )
                self.ax.set_ylabel('Volume (µL)', size=12)
                self.ax.set_xlabel('Time (s)', size=12)
                self.ax.set_xlim(0, self.tmax)

                self.df = pd.DataFrame(
                    data=np.stack([np.array(t)] + [curve for curve in areas], 1),
                    columns=['t'] + [m.name for m in self.video.masks]
                )

                if t[-1] / self.tmax > 0.95:
                    # todo: this is a bit backwards, the VideoAnalyzer object should know how
                    #  many steps it will take at a given dt and say it's done at the last step...
                    self.done = True
                    self.quit()

            except TypeError:
                pass

            if isinstance(self.df, pd.DataFrame):
                return self.df

    def keepopen(self):
        """ Called to keep the window open after the script has run. """
        self.focus()
        self.mainloop()
