import argparse

from source.videodata import *

if __name__ == '__main__':

    t = []
    areas = []

    va = VideoAnalyzer(
        video_path='char.mp4',
        overlay_path='char.svg',
        dt = 0.1,
        h = 153e-6,
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
