import isimple
from isimple.video.gui import *
from isimple.utils import restrict
import tkinter.filedialog as tkfd
from isimple.scripts.video_cli import demo


class FileSelectWindow(isimple.HistoryApp):
    """
        - Select video & overlay files
        - Edit script parameters (dt, ...)
    """

    __default_dt__ = 5
    __default_h__ = 0.153
    __history_path__ = '.history'

    __path_width__ = 60
    __num_width__ = 12

    full_history = {}
    history = {}

    video_path_history = ['']
    design_path_history = ['']
    previous_height = 0.153
    previous_timestep = 5

    def __init__(self):
        isimple.HistoryApp.__init__(self, __file__)
        self.output = (None, None, None, None)

        self.window = ScriptWindow()
        self.window.title('isimple-video')
        self.window.option_add('*Font', '12')

        self.canvas = tk.Canvas(self.window)
        self.window.bind("<Return>", self.run)

        self.video_path = tk.StringVar(value=self.video_path_history[0])
        self.design_path = tk.StringVar(value=self.design_path_history[0])
        self.timestep = tk.StringVar(value=self.previous_timestep)
        self.height = tk.StringVar(value=self.previous_height)

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
            self.window, text='Run', command=self.run
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
            'previous_timestep': 5,
            'previous_height': 0.153
        }

    def unpack_history(self):
        self.video_path_history = self.history['video_path'][::-1]
        self.design_path_history = self.history['design_path'][::-1]
        if len(self.video_path_history) > 20:
            self.video_path_history = self.video_path_history[0:19]
        if len(self.design_path_history) > 20:
            self.design_path_history = self.design_path_history[0:19]

        self.previous_timestep = self.history['previous_timestep']
        self.previous_height = self.history['previous_height']

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

    def run(self, _=None):
        video = self.video_path_box.get()
        design = self.design_path_box.get()
        height = float(self.height_box.get())
        timestep = float(self.timestep_box.get())

        try:
            self.history['video_path'].remove(video)
        except ValueError:
            pass

        try:
            self.history['design_path'].remove(design)
        except ValueError:
            pass

        self.history['video_path'] = list(set(self.history['video_path']))
        self.history['design_path'] = list(set(self.history['design_path']))

        self.history['video_path'].append(video)
        self.history['design_path'].append(design)

        self.history['previous_height'] = height
        self.history['previous_timestep'] = timestep

        self.save_history()
        self.output = (video, design, timestep, height)

        self.window.destroy()


if __name__ == '__main__':
    isimple.update()

    fs = FileSelectWindow()
    v, d, t, h = fs.output
    demo(v, d, t, h)
