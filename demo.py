import argparse

from source.videodata import *

import numpy as np
import matplotlib.pyplot as plt
import time

parser = argparse.ArgumentParser()
parser.add_argument(
    'video', help = 'Path to video file', type = str
)
parser.add_argument(
    'design', help = 'Path to design file (.svg)', type = str
)
parser.add_argument(
    '-dt', help = 'Time interval in seconds', type = float, default = 5
)
parser.add_argument(
    '-hc', help = 'Channel height in millimetres', type = float, default = 0.153
)

if __name__ == '__main__':
    args = parser.parse_args()

    t = []
    areas = []

    va = VideoAnalyzer(
        args.video, args.design, dt = args.dt, h = args.hc
    )
    va.reset()

    pw = ProgressWindow(va)

    while not va.done:
        ct = va.get_next_frame()

        if not va.done:
            areas.append(va.areas())
            t.append(ct)

            pw.plot(t=t, areas=areas)
            pw.update()

    pw.keepopen()



