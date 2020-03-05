import abc
import os
import subprocess
import sys
import time
import tkinter
import tkinter as tk
import tkinter.messagebox
from collections import namedtuple

from tkinter import filedialog as tkfd, ttk as ttk
from typing import Dict, List, Type, Union, Callable

import cv2
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import screeninfo
from PIL import Image, ImageTk
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.figure import Figure

import og.app
from isimple.core.common import RootInstance, Endpoint
from isimple.endpoints import GuiRegistry, BackendRegistry as backend

from isimple.util import restrict, rotations

try:
    __monitor_w__ = min(m.width for m in screeninfo.get_monitors())
    __monitor_h__ = min(m.height for m in screeninfo.get_monitors())
except ValueError:
    __monitor_w__ = 1920
    __monitor_h__ = 1080

__coo__ = namedtuple('Coordinate', 'x y')
__ratio__ = 0.6  # some kind of magic number?

__FIRST_FRAME__ = 1200


class OG_ScriptWindow(tk.Tk):
    def __init__(self):
        self.done = False
        tk.Tk.__init__(self)
        self.protocol("WM_DELETE_WINDOW", self.close)

    def focus(self):
        self.focus_force()

    def close(self, do_exit=True):
        """Called when user tries to close the window.
        """
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
            if tkinter.messagebox.askokcancel(
                    "Quit", "The script is still running. Really quit?"
            ):
                self.destroy()
                if do_exit:
                    sys.exit()


class OG_FileSelectWindow(og.app.HistoryApp):
    """
        - Select video & overlay files
        - Edit script parameters (dt, ...)
    """
    __history_path__ = '.history'

    __path_width__ = 60
    __num_width__ = 12

    config: dict = {}

    full_history: dict
    history: dict

    def __init__(self, WRAPPER, file=__file__):
        super().__init__(file)

        self.WRAPPER = WRAPPER
        self.config = self.WRAPPER.get_config()

        self.window = OG_ScriptWindow()
        self.window.title('isimple-video')
        self.window.option_add('*Font', '12')

        self.canvas = tk.Canvas(self.window)
        self.window.bind("<Return>", self.commit)

        self.video_path = tk.StringVar(value=self.video_path_history[0])
        self.design_path = tk.StringVar(value=self.design_path_history[0])
        self.timestep = tk.StringVar(value=self.config['dt'])
        self.height = tk.StringVar(value=self.config['height'] * 1e3)  # m to mm

        video_list = list(filter(None, self.video_path_history))
        design_list = list(filter(None, self.design_path_history))

        self.video_path_box = ttk.Combobox(
            self.canvas, values=video_list,
            textvariable=self.video_path, width=self.__path_width__
        )
        self.design_path_box = ttk.Combobox(
            self.canvas, values=design_list,
            textvariable=self.design_path, width=self.__path_width__
        )
        self.height_box = ttk.Entry(
            self.canvas,
            textvariable=self.height, width=self.__num_width__
        )
        self.timestep_box = ttk.Entry(
            self.canvas,
            textvariable=self.timestep, width=self.__num_width__
        )

        browse_video = tk.Button(
            self.canvas, text='Browse...',
            command=self.browse_video, font='Arial 10', pady=1, padx=3
        )
        browse_design = tk.Button(
            self.canvas, text='Browse...',
            command=self.browse_design, font='Arial 10', pady=1, padx=3
        )
        run_button = tk.Button(
            self.window, text='Run', command=self.commit
        )

        self.video_path_box.grid(column=1, row=1)
        self.design_path_box.grid(column=1, row=3)
        self.height_box.grid(column=2, row=1)
        self.timestep_box.grid(column=2, row=3)
        browse_video.grid(column=0, row=1)
        browse_design.grid(column=0, row=3)

        tk.Label(
            self.canvas, text="Video file: ",
            width=self.__path_width__, anchor='w'
        ).grid(column=1, row=0)
        tk.Label(
            self.canvas, text="Design file: ",
            width=self.__path_width__, anchor='w'
        ).grid(column=1, row=2)
        tk.Label(
            self.canvas, text="Height (mm): ",
            width=self.__num_width__, anchor='w'
        ).grid(column=2, row=0)
        tk.Label(
            self.canvas, text="Timestep (s): ",
            width=self.__num_width__, anchor='w'
        ).grid(column=2, row=2)

        self.canvas.pack(anchor='w', padx=5, pady=5)
        run_button.pack()
        self.window.mainloop()

    def reset_history(self):
        self.history = {
            'video_path': [''],
            'design_path': [''],
            'config': [{}]
        }

    def unpack_history(self):
        self.video_path_history = self.history['video_path'][::-1]
        self.design_path_history = self.history['design_path'][::-1]
        if len(self.video_path_history) > 20:
            self.video_path_history = self.video_path_history[0:19]
        if len(self.design_path_history) > 20:
            self.design_path_history = self.design_path_history[0:19]

        self.config = self.history['config'][-1]  # todo: only doing the last one entry, doesn't matter too much

        self.__path_width__ = max(
            [len(path) for path
             in self.video_path_history + self.design_path_history]
        )

        self.__path_width__ = restrict(self.__path_width__, 10, 200)

    def browse_video(self):
        self.video_path.set(load_file_dialog(
            'Select a video file...',
            ['*.mp4', '*.mkv', '*.avi', '*.mpg', '*.mov'], 'Video files',
        ))

    def browse_design(self):
        self.design_path.set(load_file_dialog(
            'Select a design file...',
            ['*.svg'], 'SVG files',
        ))

    def commit(self, _=None):
        self.config.update({
            'video_path': self.video_path_box.get(),
            'design_path': self.design_path_box.get(),
            'height': float(self.height_box.get()),
            'dt': float(self.timestep_box.get()),
            'frame_interval_setting': 'dt',
        })

        try:
            self.history['video_path'].remove(self.config['video_path'])
        except ValueError:
            pass

        try:
            self.history['design_path'].remove(self.config['video_path'])
        except ValueError:
            pass

        self.history['video_path'] = list(set(self.history['video_path']))
        self.history['design_path'] = list(set(self.history['design_path']))

        self.history['video_path'].append(self.config['video_path'])
        self.history['design_path'].append(self.config['design_path'])

        self.history['config'].append(self.config)

        self.save_history()

        self.WRAPPER.set_config({
            'video_path': self.config['video_path'],
            'design_path': self.config['design_path'],
            'dt': self.config['dt'],
            'height': self.config['height'] * 1e-3,  # mm to m
        })

        self.window.destroy()


class OG_ReshapeSelection:
    """Reshape-able rectangle ROI selection for tkinter canvases
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
        """Callback to clear selection rectangle
        """
        self.initialized = False
        self.has_rectangle = False
        for button in self.corners:
            button.delete()
        for line in self.lines:
            self.canvas.delete(line)

    def press(self, event):
        """Mouse press callback. Initializes rectangle dragging.
        """
        if not self.initialized:
            self.start = __coo__(x=event.x, y=event.y)
            self.initialized = True

    def release(self, event):
        """Mouse release callback. Commits rectangle dragging result.
        """
        if not self.has_rectangle:
            self.stop = __coo__(x=event.x, y=event.y)

            # Get coordinates of rectangle corners
            self.coordinates = [
                __coo__(self.start.x, self.start.y),    # Bottom Left
                __coo__(self.start.x, self.stop.y),     # ?      ?
                __coo__(self.stop.x, self.stop.y),      # ?      ?
                __coo__(self.stop.x, self.start.y)      # Top    Right
            ]

            self.get_corners()

    def get_corners(self):
        self.corners = []
        names = ['BL', '?1', '?2', 'TR']

        # Initialize corner objects
        for i, coordinate in enumerate(self.coordinates):
            self.corners.append(
                OG_Corner(self, coordinate, name=names[i])
            )

        self.has_rectangle = True
        self.update()

    def update(self):
        """Update selection rectangle and transform matrix.
        """
        self.redraw()
        co = [corner.co for corner in self.corners]

        # Permute the coordinate list
        co = [co[i] for i in self.order]

        self.transform.get_new_transform(co)

    def redraw(self):
        """Redraw selection rectangle on the canvas.
        """
        for line in self.lines:
            self.canvas.delete(line)

        for i, corner in enumerate(self.corners):
            self.lines.append(
                self.canvas.create_line(self.corners[i - 1].co, corner.co)
            )

        for corner in self.corners:
            self.canvas.focus(corner)

    def quit(self, _):
        """Close the window.
        """
        self.canvas.master.destroy()


class OG_Corner:
    """Draggable corner for ROI selection rectangle
    """

    __side__ = 35
    __fontsize__ = 12
    handle = None
    alpha = 0.05

    def __init__(self, selection, co, name=''):
        self.canvas = selection.canvas
        self.selection = selection
        self.co = co
        # self.id = self.canvas.create_oval(
        #     co.x-r, co.y-r, co.x+r, co.y+r, fill='LightGray'
        # )
        self.name = name

        self.previous = None
        self.drag_binding = None

        if self.handle is None:
            pim = Image.new(
                'RGBA',
                (self.__side__, self.__side__),
                (255, 0, 0, int(self.alpha * 255))
            )

            self.handle = ImageTk.PhotoImage(image=pim)

            # self.label = tk.Label(
            #     self.selection.window, image=self.handle, text=self.name,
            #     compound=tk.CENTER
            # )
            # self.label.place(x = co.x, y = co.y)
        if isinstance(co, __coo__):
            self.id = self.canvas.create_image(
                co.x, co.y, image=self.handle, anchor='center'
            )
        else:
            self.id = self.canvas.create_image(
                co[0], co[1], image=self.handle, anchor='center'
            )

        self.canvas.tag_bind(self.id, "<ButtonPress-1>", self.press)
        self.canvas.tag_bind(self.id, "<ButtonRelease-1>", self.release)
        # self.canvas.tag_bind(self.id, "<Enter>", self.enter)
        # self.canvas.tag_bind(self.id, "<Leave>", self.leave)

        self.dragging = False

    def press(self, event):
        """Callback for mouse click
        """
        self.previous = __coo__(event.x, event.y)
        self.drag_binding = self.canvas.bind("<Motion>", self.drag)
        self.dragging = True

    def drag(self, event):
        """Callback for mouse movement after click
        """
        self.canvas.move(
            self.id, event.x - self.previous.x, event.y - self.previous.y
        )
        co = self.canvas.coords(self.id)
        self.co = __coo__(co[0], co[1])
        # self.co = __coo__((co[0] + co[2]) / 2, (co[1] + co[3]) / 2)
        self.selection.update()
        self.previous = self.co

    def release(self, event):
        """Callback for mouse release
        """
        self.canvas.unbind("<Motion>", self.drag_binding)
        co = self.canvas.coords(self.id)
        self.co = __coo__(co[0], co[1])
        # self.co = __coo__((co[0]+co[2])/2, (co[1]+co[3])/2)
        self.selection.update()
        # self.leave(event)
        self.dragging = False

    def delete(self):
        self.canvas.delete(self.id)

    # def enter(self, _):
    #     """Callback - mouse is hovering over object
    #     """
    #     self.canvas.set_config(cursor='hand2')
    #
    # def leave(self, _):
    #     """Callback - mouse is not hovering over object anymore
    #     """
    #     if not self.dragging:
    #         self.canvas.set_config(cursor='left_ptr')


class OG_ImageDisplay:
    """OpenCV image display in tkinter canvas with link to ROI selection
        and coordinate transform.
    """
    __ratio__ = __ratio__ * __monitor_w__
    __rotations__ = {str(p): p for p in rotations(list(range(4)))}

    def __init__(self, window: OG_ScriptWindow, order = (0, 1, 2, 3), initial_coordinates=None):
        self.window = window  # todo: some of this should actually be in an 'app' or 'window' object

        self.Nf = self.window.WRAPPER.get_total_frames()
        overlay = self.window.WRAPPER.get_overlay()
        self.frame_number = int(self.Nf/2)
        image = self.window.WRAPPER.get_raw_frame(self.frame_number)

        self.shape = image.shape

        self.__ratio__ = self.__ratio__ / self.shape[1]

        self.__width__ = int(self.shape[1] * self.__ratio__) + \
            overlay.shape[1] * self.__ratio__

        if self.__width__ >= __monitor_w__:
            self.__width__ = __monitor_w__ * 0.90
            self.__ratio__ = self.__width__ \
                / (self.shape[1] + overlay.shape[1])

        if initial_coordinates is None:
            video_coordinates = self.window.WRAPPER.get_coordinates()
            if video_coordinates is not None:
                initial_coordinates = np.array(video_coordinates) * self.__ratio__
                initial_coordinates = initial_coordinates.tolist()

        self.canvas = tk.Canvas(
            self.window,
            width=self.__width__,
            height=max(
                int(self.shape[0] * self.__ratio__),
                int(overlay.shape[0] * self.__ratio__)
            )
        )
        self.canvas.pack()
        self.scaled_shape = (
            int(self.shape[1] * self.__ratio__),
            int(self.shape[0] * self.__ratio__)
        )

        self.original = image
        height, width, channels = image.shape
        img = cv2.cvtColor(image, cv2.COLOR_HSV2RGB)
        img = Image.fromarray(img)
        img.thumbnail(
            (int(width * self.__ratio__), int(height * self.__ratio__))
        )
        self.display_image = img
        self.tkimage = ImageTk.PhotoImage(image=img)
        self.canvas.create_image(0, 0, image=self.tkimage, anchor=tk.NW)

        self.transform = OG_TransformImage(
            self.canvas,
            image,
            overlay,
            self.scaled_shape,
            self.window.WRAPPER.estimate_transform,
            self.__ratio__,
            order,
            self.frame_number
        )
        self.selection = OG_ReshapeSelection(
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


class OG_TransformImage:
    """OpenCV perspective transform
        overlay alpha blending and display with tkinter
    """
    alpha = 0.1

    def __init__(self, canvas, image, overlay_img, co, callback, ratio, initial_order=(0, 1, 2, 3), frame_number=0):
        self.overlay = overlay_img
        self.original = image
        self.image = None
        self.img = None  # todo: image and img :)
        self.canvas = canvas
        self.callback = callback
        self.__ratio__ = ratio
        self.frame_number = frame_number

        shape = self.overlay.shape

        self.co = co
        self.height = co[1]
        self.width = int(shape[0] * co[1] / shape[1])

        self.order = initial_order
        self.show_overlay()

    def get_new_transform(self, from_coordinates):  # todo: don't need order here?
        """Recalculate transform and show overlay.
        """
        self.canvas._root().WRAPPER.estimate_transform(
            np.float32(from_coordinates) / self.__ratio__
        )

        # Round to remove unnecessary precision
        # self.transform = np.around(self.transform, decimals=3)

        # pret = cv2.warpPerspective(
        #     self.original, self.pre_transform, (X0,Y0)
        # )

        self.update()

    def update(self):
        """Update image based
        """
        y, x, c = self.overlay.shape

        self.image = self.canvas._root().WRAPPER.overlay_frame(
            self.canvas._root().WRAPPER.transform(self.original)
        )

        height, width, channels = self.overlay.shape
        img = cv2.cvtColor(self.image, cv2.COLOR_HSV2RGB)
        img = Image.fromarray(img)
        img.thumbnail(
            (int(width * self.__ratio__), int(height * self.__ratio__))
        )
        self.img = ImageTk.PhotoImage(image=img)
        self.canvas.create_image(self.co[0], 0, image=self.img, anchor=tk.NW)

        # self.callback(self.transform)

    def show_overlay(self):
        """Show overlay; i.e. without the acual video frame
        """
        height, width, channels = self.overlay.shape
        img = cv2.cvtColor(self.overlay, cv2.COLOR_BGR2RGB)
        img = Image.fromarray(img)
        img.thumbnail(
            (int(width * self.__ratio__), int(height * self.__ratio__))
        )
        img = ImageTk.PhotoImage(image=img)
        self.canvas.create_image(self.co[0], 0, image=img, anchor=tk.NW)


def hsvimg2tk(image, ratio=1.0):
    """Convert OpenCV HSV image to PhotoImage object
    """
    img = cv2.cvtColor(image, cv2.COLOR_HSV2RGB)
    shape = img.shape
    img = Image.fromarray(img)
    img.thumbnail(
        (int(shape[1] * ratio), int(shape[0] * ratio))
    )
    img = ImageTk.PhotoImage(image=img)
    return img


def bgrimg2tk(image, ratio=1.0):
    """Convert OpenCV HSV image to PhotoImage object
    """
    img = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    shape = img.shape
    img = Image.fromarray(img)
    img.thumbnail(
        (int(shape[1] * ratio), int(shape[0] * ratio))
    )
    img = ImageTk.PhotoImage(image=img)
    return img


def binimg2tk(image, ratio=1.0):
    """Convert OpenCV binary image to PhotoImage object
    """
    img = cv2.cvtColor(image, cv2.COLOR_GRAY2RGB)
    shape = img.shape
    img = Image.fromarray(img)
    img.thumbnail(
        (int(shape[1] * ratio), int(shape[0] * ratio))
    )
    img = ImageTk.PhotoImage(image=img)
    return img


class OG_ColorPicker:
    """Select colours by clicking image pixels.
    """
    __w_spacing__ = 3
    __h_scale__ = 25

    def __init__(self, window, WRAPPER):
        self.window = window
        self.WRAPPER = WRAPPER

        self.coo = None

        self.FN = 1
        image = self.WRAPPER.mask(self.WRAPPER.get_frame(self.FN))

        self.filter = self.WRAPPER.get_filter_parameters()

        self.im_masked = None
        self.im_filtered = None

        self.__width__ = image.shape[1] * 2 + self.__w_spacing__,

        if isinstance(self.__width__, tuple):
            self.__width__ = self.__width__[0]

        if self.__width__ >= __monitor_w__:
            self.__width__ = __monitor_w__ * 0.98
            self.__ratio__ = \
                self.__width__ / (image.shape[1] * 2 + self.__w_spacing__)
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
            to=self.WRAPPER.get_total_frames(),
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
        """Update UI
        """
        frame = self.WRAPPER.get_frame(self.FN)
        masked = self.WRAPPER.mask(frame)
        filtered = self.WRAPPER.filter(masked)

        self.im_masked = hsvimg2tk(masked, ratio=self.__ratio__)
        self.im_filtered = binimg2tk(filtered, ratio=self.__ratio__)

        self.masked = masked

        self.canvas.create_image(
            0, 0,
            image=self.im_masked, anchor=tk.NW
        )
        self.canvas.create_image(
            self.center + self.__w_spacing__, 0,
            image=self.im_filtered, anchor=tk.NW
        )

        self.window.selection_callback()

    def pick(self, event):
        """Pick a colour
        """
        self.coo = __coo__(x=event.x, y=event.y)
        self.filter = self.WRAPPER.get_filter_parameters()
        self.filter = self.WRAPPER.set_filter_parameters(self.filter, tuple(self.masked[self.coo.y, self.coo.x]))
        self.update()

    def track(self, value):
        """Scrollbar callback - track through the video.
        """
        self.FN = int(value)
        self.update()

    def quit(self, _):
        """Close the window.
        """
        self.window.destroy()


class OG_OverlayAlignWindow(OG_ScriptWindow):
    __default_frame__ = 0.5
    __title__ = "Overlay alignment"

    def __init__(self, WRAPPER):
        OG_ScriptWindow.__init__(self)
        self.WRAPPER = WRAPPER
        self.title(self.__title__)

        self.image = OG_ImageDisplay(self)


class OG_MaskFilterWindow(OG_ScriptWindow):
    __title__ = 'Filter hue selection'

    def __init__(self, WRAPPER):
        OG_ScriptWindow.__init__(self)
        self.WRAPPER = WRAPPER
        self.title('Pick a color')

        self.picker = OG_ColorPicker(
            self, self.WRAPPER
        )

    def selection_callback(self):  # todo: don't need selection here?
        self.done = True


class OG_ProgressWindow(OG_ScriptWindow):
    __ratio__ = 0.25
    __plot_pad__ = 0.075
    __pad__ = 2
    __dpi__ = 100

    __title__ = 'Volume measurement'

    def __init__(self, WRAPPER):
        OG_ScriptWindow.__init__(self)
        self.WRAPPER = WRAPPER
        self.title(self.WRAPPER.get_name())

        self.canvas_height = self.__ratio__ * __monitor_h__

        frame = self.WRAPPER.get_raw_frame(0)
        state = self.WRAPPER.get_frame(0)

        self.colors = self.WRAPPER.get_colors()[0]  # We assume that there's only one featureset for now
        self.mask_names = self.WRAPPER.get_mask_names()
        self.t = []

        self.__raw_width__ = frame.shape[1] * \
                             self.canvas_height / frame.shape[0]
        self.__processed__ = state.shape[1] * \
                             self.canvas_height / state.shape[0]

        self.tmax = self.WRAPPER.get_total_frames() / self.WRAPPER.get_fps()
        self.t0 = time.time()

        self.img = None
        self.df = None
        self.t = []
        self.areas = [[] for _ in self.colors]
        self.size = frame.shape

        self.canvas_width = \
            self.__raw_width__ + self.__processed__ + self.__pad__

        self.canvas = tk.Canvas(
            self,
            width=self.canvas_width,
            height=self.canvas_height
        )
        self.update_image(np.ones(state.shape, dtype = state.dtype), frame)
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
        self.figcanvas.get_tk_widget().pack(
            side=tk.BOTTOM, fill=tk.BOTH, expand=1
        )

        self.figcanvas.get_tk_widget().pack()

    def update_image(self, state, frame):
        """Show the current video frame in the UI
        """
        if isinstance(state, list):
            state = state[0]  # assuming that we have only one feature set

        if frame is not None:
            self.img = hsvimg2tk(
                frame,
                ratio=self.canvas_height / frame.shape[0]
            )
            self.state = bgrimg2tk(
                state,
                ratio=self.canvas_height / state.shape[0],
            )
            self.canvas.create_image(
                0, 0, image=self.img, anchor=tk.NW
            )
            self.canvas.create_image(
                self.__raw_width__ + self.__pad__, 1,
                image=self.state, anchor=tk.NW
            )

    def update_window(self, time, values, state, frame):
        self.plot(time, values)
        self.update_image(state, frame)

        self.figcanvas.draw()
        OG_ScriptWindow.update(self)

    def plot(self, t, areas):  # todo: this should call a method in isimple.video.visualization
        """Update the plot.
        """
        if areas is not None:

            if not hasattr(self, 'areas'):
                self.areas = []

            if not hasattr(self, 't'):
                self.t = []

            self.t.append(t)
            for i, value in enumerate(areas[0]):
                self.areas[i].append(value)

            elapsed = time.time() - self.t0

            self.ax.clear()
            for i, curve in enumerate(self.areas):
                color = cv2.cvtColor(
                    np.array([[
                        np.array(
                            self.colors[i],
                            dtype=np.uint8
                        )
                    ]]),
                    cv2.COLOR_HSV2RGB
                )[0, 0] / 255
                # todo: shouldn't need to do this calculation at every time step!
                self.ax.plot(
                    self.t, curve,
                    label=self.mask_names[i],
                    color=tuple(color),
                    linewidth=2
                )

            # todo: is it necessary to re-do all of the plot legend/axis stuff for every time step?
            self.ax.legend(loc='center right')
            self.ax.set_title(
                f"{self.t[-1] / self.tmax * 100:.0f}% ({elapsed:.0f} s elapsed "
                f" @ {self.t[-1] / elapsed:.1f} x)", size=18, weight='bold'
            )
            self.ax.set_ylabel('Volume (µL)', size=12)
            self.ax.set_xlabel('Time (s)', size=12)
            self.ax.set_xlim(0, self.tmax)

            self.df = pd.DataFrame(
                data=np.stack(
                    [np.array(self.t)] + [curve for curve in self.areas], 1),
                columns=['t'] + list(self.mask_names)
            )

            if self.t[-1] / self.tmax > 0.95:
                # todo: this is a bit backwards, the VideoAnalyzer object should know how
                #  many steps it will take at a given dt and say it's done at the last step...
                self.done = True
                self.quit()

        if isinstance(self.df, pd.DataFrame):
            return self.df

    def keepopen(self):
        """Called to keep the window open after the script has run.
        """
        self.focus()
        self.mainloop()


def has_zenity():
    try:
        with open(os.devnull, 'w') as null:
            return not subprocess.check_call(['zenity', '--version'], stdout=null)
    except FileNotFoundError:
        return False


def load_file_dialog(title: str = None, patterns: List[str] = None, patterns_str: str = None):
    if title is None:
        title = 'Load...'

    if patterns is None:
        patterns = []

    if has_zenity():
        try:
            if len(patterns) > 0:
                p = subprocess.Popen(
                    [
                        'zenity', '--file-selection',
                        f'--file-filter', ' '.join(patterns),
                    ], stdout=subprocess.PIPE, stderr=subprocess.PIPE
                )
            else:
                p = subprocess.Popen(
                    [
                        'zenity', '--file-selection',
                    ], stdout=subprocess.PIPE, stderr=subprocess.PIPE
                )
            out, err = p.communicate()
            if not err:
                return out.rstrip().decode('utf-8')
        except subprocess.CalledProcessError:
            return None

    else:
        if len(patterns) > 0:
            return tkfd.askopenfilename(
                title=title,
                filetypes=[(patterns_str, ' '.join(patterns))]
            )
        else:
            return tkfd.askopenfilename(
                title=title,
            )


def save_file_dialog(title: str = None, patterns: List[str] = None, patterns_str: str = None):
    if title is None:
        title = 'Save as...'

    if patterns is None:
        patterns = []

    if has_zenity():
        try:
            if len(patterns) > 0:
                p = subprocess.Popen(
                    [
                        'zenity', '--file-selection', '--save'
                        f'--file-filter', ' '.join(patterns),
                    ], stdout=subprocess.PIPE, stderr=subprocess.PIPE
                )
            else:
                p = subprocess.Popen(
                    [
                        'zenity', '--file-selection', '--save'
                    ], stdout=subprocess.PIPE, stderr=subprocess.PIPE
                )
            out, err = p.communicate()
            if not err:
                return out.strip().decode('utf-8')
        except subprocess.CalledProcessError:
            return None

    else:
        if len(patterns) > 0:
            return tkfd.asksaveasfilename(
                title=title,
                filetypes=[(patterns_str, ' '.join(patterns))]
            )
        else:
            return tkfd.asksaveasfilename(
                title=title,
            )


class EntryPopup(ttk.Entry):
    """Pop-up widget to allow value editing in TreeDict
    """
    def __init__(self, parent, iid, index, item, callback, **kw):
        ''' If relwidth is set, then width is ignored '''
        super().__init__(parent, **kw)
        self.tv = parent
        self.iid = iid
        self.item = item
        self.callback = callback

        self.index = index
        self.insert(0, self.tv.item(self.iid, "values")[index])
        # self['state'] = 'readonly'
        # self['readonlybackground'] = 'white'
        # self['selectbackground'] = '#1BA1E2'
        self['exportselection'] = False

        self.focus_force()
        self.bind("<Return>", self.on_return)  # todo: this doesn't work too well. Also bind numpad enter & "click away / unfocus"
        self.bind("<KP_Enter>", self.on_return)
        self.bind("<Control-a>", self.select_all)
        self.bind("<Escape>", lambda *ignore: self.destroy())
        self.bind("<FocusOut>", lambda *ignore: self.destroy())

    def on_return(self, event):
        v = list(self.tv.item(self.iid, "values"))
        v[self.index] = self.get()
        self.tv.item(self.iid, values=tuple(v))  # todo: also update self.tv._data !!!

        self.item = type(self.item)(v[0])

        self.callback()
        self.destroy()

    def select_all(self, *ignore):
        ''' Set selection on the whole text '''
        self.selection_range(0, 'end')

        # returns 'break' to interrupt default key-bindings
        return 'break'


class TreeDict(object):
    """An editable representation of a dictionary in a ttk.Treeview
    """

    # cheated off of
    #   - https://github.com/r2123b/tkinter-ttk-Treeview-Simple-Demo/blob/master/SimpleTreeview.py
    #   - https://stackoverflow.com/questions/51762835/
    #   - https://stackoverflow.com/questions/18562123/

    _tk: Union[tkinter.Tk, tkinter.Misc]
    _tree: ttk.Treeview
    _data: dict

    _values: Dict[str, list]
    _edit_callback: Callable[[dict], dict]

    _data_iid: dict

    def __init__(self, tk: Union[tkinter.Tk, tkinter.Misc], data: dict, callback: Callable[[dict], dict]):
        self._tk = tk
        self._edit_callback = callback  # type: ignore
        self.update(data)

        self._tree.bind("<Double-1>", self.edit)

    def set(self, data: dict):
        self._data = data
        self.build()

    def set_value(self, iid, value):
        raise NotImplementedError

    def callback(self):
        self._data = self._edit_callback(self._data)  # callback to handler; validate & update self._data

    def build(self):
        self._tree = ttk.Treeview(
            self._tk, show="tree"
        )
        self._iid_mapping = {}

        def handle_item(self, key, item, parent: str = ''):
            if (isinstance(item, list) or isinstance(item, tuple)) and \
                    not any(isinstance(i, dict) for i in item):
                p = self._tree.insert(parent, 'end', text=key, values=[str(item)])
                self._iid_mapping[p] = item
            elif (isinstance(item, list) or isinstance(item, tuple)) and \
                    any(isinstance(i, dict) for i in item):
                p = self._tree.insert(parent, 'end', text=key)
                self._iid_mapping[p] = item
                for i, subitem in enumerate(item):
                    if 'name' in subitem:
                        title = subitem['name']
                    else:
                        title = f"{key} {i}"
                    handle_item(self, title, subitem, p)
            elif isinstance(item, dict):
                p = self._tree.insert(parent, 'end', text=key)
                self._iid_mapping[p] = item
                for sk, sv in item.items():
                    handle_item(self, sk, sv, p)
            else:
                p = self._tree.insert(parent, 'end', text=key, values=[item])
                self._iid_mapping[p] = item
            self._tree.item(p, open=True)  # expands everything by default

        for k, v in self._data.items():
            handle_item(self, k, v)

        self._tree["columns"] = ('', '')  # doesn't work with *one* column or when not set, for some reason


    def edit(self, event):
        ''' Executed, when a row is double-clicked. Opens
        read-only EntryPopup above the item's column, so it is possible
        to select text '''

        # close previous popups
        if hasattr(self, 'entryPopup'):
            try:
                self.entryPopup.on_return(None)
            except Exception:
                pass
            self.entryPopup.destroy()
            del self.entryPopup

        # what row and column was clicked on
        rowid = self._tree.identify_row(event.y)
        column = self._tree.identify_column(event.x)

        print(f"Selected row {rowid} & column {column}")

        # Don't allow editing keys
        if column != '#0':
            # get column position info
            x, y, width, height = self._tree.bbox(rowid, column)

            print(f"Cell: x{x}, y{y}, x{width}, h{height}")

            # y-axis offset
            pady = height // 2
            # pady = 0

            # place Entry popup properly
            index = int(column[1:]) - 1
            self.entryPopup = EntryPopup(self._tree, rowid, index, self._iid_mapping[rowid], self.callback)
            self.entryPopup.place(x=x, y=y + pady, anchor='w', width=100)  # todo: set x to start at the right column, relwidth to cover the whole column

    def update(self, data: dict):
        self.set(data)
        self._tree.pack()
        self._tk.update()


class guiElement(abc.ABC):
    """Abstract class for GUI elements
    """
    def __init__(self):
        pass

    def build(self):
        pass


class guiPane(guiElement):
    """Abstract class for a GUI pane
    """
    def __init__(self):
        super().__init__()

    def build(self):
        pass


gui = GuiRegistry()


class guiWindow(guiElement):
    """Abstract class for a GUI window
    """
    _endpoints: List[Endpoint]

    def __init__(self):
        super().__init__()

    def open(self):  # todo: should check if all callbacks have been provided
        pass

    def close(self):
        pass


class SetupWindow(guiWindow):
    _endpoints = [
        backend.get_config,
        backend.set_config,
    ]

    def __init__(self):  # todo: should limit configuration get/set to backend; metadata saving should be done from there too.
        super().__init__()

    def open(self):
        og.gui.OG_FileSelectWindow(self)


class TransformWindow(guiWindow):
    """Allows the user to set up a transform interactively
            * Callbacks:
                - Get the raw and transformed frame at a certain frame number (scrollable)
                - Estimate the transform for a set of coordinates
        """
    _endpoints = [
        backend.get_total_frames,
        backend.get_overlay,
        backend.overlay_frame,
        backend.get_raw_frame,
        backend.transform,
        backend.estimate_transform,
        backend.get_coordinates,
        backend.get_frame,
        backend.get_overlaid_frame,
        backend.get_inverse_transformed_overlay,
    ]

    def __init__(self):
        super().__init__()

    def open(self):
        og.gui.OG_OverlayAlignWindow(self)


class FilterWindow(guiWindow):
    """Allows the user to set up a filter interactively
        * Interaction:
            - Scroll through the video to find the liquid of interest,
              click on it and set the filter according to the selected pixel
            - todo: extra GUI elements for more control over filter parameters
            - todo: would be great to change the filter *type* dynamically; in that
                    case the gui Manager would have to be involved in order to
                    update the FilterWindow's callbacks...
                    Otherwise: filter implementations wrapped by Filter, not
                    inheriting from Filter
        * Callbacks:
            - Get the masked / masked & filtered frame at a certain frame number (scrollable)
            - Set the filter
    """
    _endpoints = [
        backend.get_total_frames,
        backend.get_frame,
        backend.mask,
        backend.get_filter_parameters,
        backend.set_filter_parameters,
        backend.filter,
    ]

    def __init__(self):
        super().__init__()

    def open(self):
        og.gui.OG_MaskFilterWindow(self)


class ProgressWindow(guiWindow):
    """Shows the progress of an analysis.
        * No callbacks; not interactive, so the backend pushes to the GUI instead
    """
    _endpoints = [
        backend.get_colors,
        backend.get_frame,
        backend.get_raw_frame,
        backend.get_total_frames,
        backend.get_fps,
        backend.get_dpi,
        backend.get_mask_names,
    ]

    def __init__(self):
        super().__init__()

    def open(self):
        self.pw = og.gui.OG_ProgressWindow(self)

    @gui.expose(gui.update_progresswindow)
    def update(self, time: float, values: list, state: np.ndarray, frame: np.ndarray) -> None:
        self.pw.update_window(time, values, state, frame)


class VideoAnalyzerGui(RootInstance, guiElement):  # todo: find a different name
    windows: Dict[type, guiWindow]
    open_windows: List[guiWindow]

    _instances: List[guiElement]
    _instance_class = guiElement

    _backend: RootInstance
    _endpoints: GuiRegistry = gui

    def __init__(self, backend: RootInstance):
        super().__init__()

        self.windows = {}
        self.open_windows = []

        self._backend = backend
        self._backend.connect(self)

        for c in [SetupWindow, TransformWindow, FilterWindow, ProgressWindow]:  # todo: cleaner way to define this, maybe as a _window_classes class attribute?
            self.add_window(c)

        self._gather_instances()

    @gui.expose(gui.open_setupwindow)
    def open_setupwindow(self) -> None:  # todo: probably a bad idea to give out references to the actual windows; maybe give index or key instead?
        self.open_window(SetupWindow)

    @gui.expose(gui.open_transformwindow)
    def open_transformwindow(self) -> None:
        self.open_window(TransformWindow)

    @gui.expose(gui.open_filterwindow)
    def open_filterwindow(self, index: int) -> None:
        self.open_window(FilterWindow, index)

    @gui.expose(gui.open_progresswindow)
    def open_progresswindow(self) -> None:
        self.open_window(ProgressWindow)

    def add_window(self, window_type: Type[guiWindow]):
        self.windows[window_type] = window_type()


    def open_window(self, window_type: Type[guiWindow], index: int = None):
        w = self.windows[window_type]

        if isinstance(w, list):
            if index is None:
                index = 0
            w = w[index]

        self.open_windows.append(w)

        for endpoint in w._endpoints:
            setattr(w, endpoint._name, self._backend.get(endpoint, index))

        w.open()

    def close_window(self, index: int):
        window = self.open_windows.pop(index)
        window.close()

    def wait_on_close(self, window):  # todo: windows should run in separate threads
        # todo: check that window is in self.windows
        while window.is_open:  # todo: wrap Thread.join() instead
            time.sleep(0.05)

    def close_all_windows(self):
        if hasattr(self, 'windows'):
            for window in self.open_windows:
                window.close()

            self.open_windows = []
