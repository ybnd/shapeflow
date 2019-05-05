from source.gui import *
from io import StringIO
import tkinter.filedialog as tkfd
from demo import demo


class FileSelectWindow:
    """
        - Select video & overlay files
        - Edit script parameters (dt, ...)
    """

    __default_dt__ = 5
    __default_h__ = 0.153
    __history_path__ = '.history'

    __path_width__ = 60
    __num_width__ = 12

    def __init__(self):
        self.window = ScriptWindow()
        self.window.title('isimple-video')
        self.window.option_add('*Font', '48')
        self.read_history()

        self.canvas = tk.Canvas(self.window)

        self.video_path = tk.StringVar(value=self.video_path_history[0])
        self.design_path = tk.StringVar(value=self.design_path_history[0])
        self.timestep = tk.StringVar(value=self.previous_timestep)
        self.height = tk.StringVar(value=self.previous_height)

        video_list = list(filter(None, self.video_path_history))
        design_list = list(filter(None, self.design_path_history))

        self.video_path_box = ttk.Combobox(self.canvas, values=video_list, textvariable=self.video_path, width=self.__path_width__)
        self.design_path_box = ttk.Combobox(self.canvas, values=design_list, textvariable=self.design_path, width=self.__path_width__)
        self.height_box = ttk.Entry(self.canvas, textvariable=self.height, width=self.__num_width__)
        self.timestep_box = ttk.Entry(self.canvas, textvariable=self.timestep, width=self.__num_width__)

        browse_video = tk.Button(self.canvas, text='Browse...', command=self.browse_video, font='System 11', pady=1, padx=3)
        browse_design = tk.Button(self.canvas, text='Browse...', command=self.browse_design, font='System 11', pady=1, padx=3)
        run = tk.Button(self.window, text='Run', command=self.run)

        self.video_path_box.grid(column=1, row=1)
        self.design_path_box.grid(column=1, row=3)
        self.height_box.grid(column=2, row=1)
        self.timestep_box.grid(column=2, row=3)
        browse_video.grid(column=0, row=1)
        browse_design.grid(column=0, row=3)

        video_label = tk.Label(self.canvas, text="Video file: ", width=self.__path_width__, anchor='w').grid(column=1, row=0)
        design_label = tk.Label(self.canvas, text="Design file: ", width=self.__path_width__, anchor='w').grid(column=1, row=2)
        height_label = tk.Label(self.canvas, text="Height (mm): ", width=self.__num_width__, anchor='w').grid(column=2, row=0)
        timestep_label = tk.Label(self.canvas, text="Timestep (s): ", width=self.__num_width__, anchor='w').grid(column=2, row=2)

        self.canvas.pack(anchor='w', padx=5, pady=5)
        run.pack()
        self.window.mainloop()

    def read_history(self):
        if os.path.isfile(self.__history_path__):
            try:
                with open(self.__history_path__, 'r') as f:
                    self.history = json.load(f)
            except json.decoder.JSONDecodeError:
                raise IOError('Invalid .history file -- delete it to reset the history')

            self.video_path_history = self.history['video_path'][::-1]
            self.design_path_history = self.history['design_path'][::-1]
            self.previous_timestep = self.history['previous_timestep']
            self.previous_height = self.history['previous_height']

            self.__path_width__ = max([len(path) for path in self.video_path_history + self.design_path_history]) - 5
        else:
            self.video_path_history = ['']
            self.design_path_history = ['']
            self.previous_height = 0.153
            self.previous_timestep = 5
            self.history = {
                'video_path': self.video_path_history,
                'design_path': self.design_path_history,
                'previous_height': self.previous_height,
                'previous_timestep': self.previous_timestep
            }

    def save_history(self):
        with open(self.__history_path__, 'w+') as f:
            json.dump(self.history, f, indent=2)

    def browse_video(self):
        self.video_path.set(tkfd.askopenfilename(filetypes=[('Video files', '*.mp4 *.mkv *.avi *.mpg *.mov')]))

    def browse_design(self):
        self.design_path.set(tkfd.askopenfilename(filetypes=[('SVG files', '*.svg')]))

    def run(self):
        video = self.video_path_box.get()
        design = self.design_path_box.get()
        height = self.height_box.get()
        timestep = self.timestep_box.get()

        self.history['video_path'].append(video)
        self.history['design_path'].append(design)

        self.history['video_path'] = list(set(self.history['video_path']))
        self.history['design_path'] = list(set(self.history['design_path']))

        self.history['previous_height'] = height
        self.history['previous_timestep'] = timestep

        self.save_history()

        with open('.run-demo', 'w+') as f:
            json.dump({'v': video, 'd': design, 'h': float(height), 't': float(timestep)}, f) # todo: lame workaround

        self.window.destroy()



if __name__ == '__main__':
    FileSelectWindow()

    with open('.run-demo', 'r') as f: args = json.load(f) # todo: lame workaround
    os.remove('.run-demo')

    demo(args['v'], args['d'], args['t'], args['h'])