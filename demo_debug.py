import argparse

from source.videodata import *

if __name__ == '__main__':

    t = []
    areas = []

    va = VideoAnalyzer(
        video_path='francesco1.mp4',
        overlay_path='fabday.svg',
        dt = 5,
        h = 0.153,
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