import isimple
from isimple.video.videodata import *


if __name__ == '__main__':
    isimple.update()

    t = []
    areas = []

    va = VideoAnalyzer(
        video_path='dries.mp4',
        overlay_path='dries.svg',
        dt=20,
        h=0.153,
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
