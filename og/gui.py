import sys
import time
import tkinter as tk
import tkinter.messagebox
from collections import namedtuple

import tkinter.ttk as ttk
import tkinter.filedialog as tkfd

import cv2
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import screeninfo
from PIL import Image, ImageTk
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.figure import Figure

import og.app

from isimple.core.util import restrict, rotations

try:
    __monitor_w__ = min(m.width for m in screeninfo.get_monitors())
    __monitor_h__ = min(m.height for m in screeninfo.get_monitors())
except ValueError:
    __monitor_w__ = 0
    __monitor_h__ = 0

__coo__ = namedtuple('Coordinate', 'x y')
__ratio__ = 0.6  # some kind of magic number?

__FIRST_FRAME__ = 1200


class ScriptWindow(tk.Tk):
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


class FileSelectWindow(og.app.HistoryApp):
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

        self.window = ScriptWindow()
        self.window.title('isimple-video')
        self.window.option_add('*Font', '12')

        self.canvas = tk.Canvas(self.window)
        self.window.bind("<Return>", self.commit)

        self.video_path = tk.StringVar(value=self.video_path_history[0])
        self.design_path = tk.StringVar(value=self.design_path_history[0])
        self.timestep = tk.StringVar(value=self.config['dt'])
        self.height = tk.StringVar(value=self.config['height'])

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
        self.video_path.set(tkfd.askopenfilename(
            filetypes=[('Video files', '*.mp4 *.mkv *.avi *.mpg *.mov')])
        )

    def browse_design(self):
        self.design_path.set(tkfd.askopenfilename(
            filetypes=[('SVG files', '*.svg')])
        )

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

        self.WRAPPER.set_config(self.config)

        self.window.destroy()


class ReshapeSelection:
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
                Corner(self, coordinate, name=names[i])
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


class Corner:
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


class ImageDisplay:
    """OpenCV image display in tkinter canvas with link to ROI selection
        and coordinate transform.
    """
    __ratio__ = __ratio__ * __monitor_w__
    __rotations__ = {str(p): p for p in rotations(list(range(4)))}

    def __init__(self, window: ScriptWindow, order = (0, 1, 2, 3), initial_coordinates=None):
        self.window = window  # todo: some of this should actually be in an 'app' or 'window' object

        self.Nf = self.window.WRAPPER.get_total_frames()
        overlay = self.window.WRAPPER.get_overlay()
        self.frame_number = int(self.Nf/2)
        image = self.window.WRAPPER.get_raw_frame(self.frame_number)

        self.shape = image.shape

        self.__ratio__ = self.__ratio__ / self.shape[1]

        if initial_coordinates is None:
            initial_coordinates = np.array(
                self.window.WRAPPER.get_coordinates()
            ) * self.__ratio__
            initial_coordinates = initial_coordinates.tolist()

        self.__width__ = int(self.shape[1] * self.__ratio__) + \
            overlay.shape[1] * self.__ratio__

        if self.__width__ >= __monitor_w__:
            self.__width__ = __monitor_w__ * 0.90
            self.__ratio__ = self.__width__ \
                / (self.shape[1] + overlay.shape[1])

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

        self.transform = TransformImage(
            self.canvas,
            image,
            overlay,
            self.scaled_shape,
            self.window.WRAPPER.estimate_transform,
            self.__ratio__,
            order,
            self.frame_number
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


class ColorPicker:
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


class OverlayAlignWindow(ScriptWindow):
    __default_frame__ = 0.5
    __title__ = "Overlay alignment"

    def __init__(self, WRAPPER):
        ScriptWindow.__init__(self)
        self.WRAPPER = WRAPPER
        self.title(self.__title__)

        self.image = ImageDisplay(self)


class MaskFilterWindow(ScriptWindow):
    __title__ = 'Filter hue selection'

    def __init__(self, WRAPPER):
        ScriptWindow.__init__(self)
        self.WRAPPER = WRAPPER
        self.title('Pick a color')

        self.picker = ColorPicker(
            self, self.WRAPPER
        )

    def selection_callback(self):  # todo: don't need selection here?
        self.done = True


class ProgressWindow(ScriptWindow):
    __ratio__ = 0.25
    __plot_pad__ = 0.075
    __pad__ = 2
    __dpi__ = 100

    __title__ = 'Volume measurement'

    def __init__(self, WRAPPER):
        ScriptWindow.__init__(self)
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
        ScriptWindow.update(self)

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

            areas = np.transpose(areas) / (
                    self.WRAPPER.get_dpi() / 25.4
            ) ** 2 * self.WRAPPER.get_h()
            # todo: do this at the VideoAnalyzer level!

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
