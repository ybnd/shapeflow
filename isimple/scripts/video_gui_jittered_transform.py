import numpy as np

import isimple
from isimple.scripts.video_gui import FileSelectWindow
from isimple.video import video_analysis_demo_jitter_transform

if __name__ == '__main__':
    isimple.update()
    fs = FileSelectWindow(__file__)

    N_jitters = int(input('Number of jittered transformations: '))
    interval = tuple(map(float, input('Jitter intensity interval: ').split(',')))

    jitters = []
    for i in range(N_jitters):
        jitters.append(np.random.uniform(min(interval), max(interval), size=(3, 3)))

    video_analysis_demo_jitter_transform(*fs.args, jitters)
