import argparse

from source.videodata import *

if __name__ == '__main__':

    t = []
    areas = []

    va = VideoAnalyzer(
        video_path='SIMPLEchar-video.mp4',
        overlay_path='SIMPLEchar-analysis.svg',
        dt = 0.5,
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