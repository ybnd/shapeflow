from isimple.video.videodata import *
from datetime import datetime


def demo(video, design, timestep, height):
    t = []
    areas = []

    va = VideoAnalyzer(
        video, design, dt=timestep, h=height
    )
    va.reset()

    pw = ProgressWindow(va)

    df = pd.DataFrame()
    while not va.done:  # todo: do this at the VideoAnalyzer level.
        ct = va.get_next_frame()

        areas.append(va.areas())
        t.append(ct)

        df = pw.plot(t=t, areas=areas)
        pw.update()

    df.to_excel(os.path.splitext(pw.video.name)[0] + ' ' + datetime.now().strftime("%Y-%m-%d %H-%M-%S") + '.xlsx', index=False)
    pw.done = True
    pw.keepopen()