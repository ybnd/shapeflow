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

    xlsx = os.path.splitext(pw.video.name)[0] + ' ' + datetime.now().strftime("%Y-%m-%d %H-%M-%S") + '.xlsx';

    writer = pd.ExcelWriter(xlsx)
    df.to_excel(
        writer, index=False, sheet_name='data'
    )
    meta = va.get_meta()
    df = pd.DataFrame.from_dict(meta)
    df.to_excel(
        writer, index=False, sheet_name='metadata'
    )
    writer.save()
    writer.close()

    pw.done = True
    pw.keepopen()
