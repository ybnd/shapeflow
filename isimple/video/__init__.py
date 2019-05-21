import os
import pandas as pd

import isimple.video.videodata
import isimple.video.metadata
from datetime import datetime


def video_analysis_demo(video, design, timestep, height):
    t = []
    areas = []

    va = isimple.video.videodata.VideoAnalyzer(
        video, design, dt=timestep, h=height
    )
    va.reset()

    xlsx = os.path.splitext(va.name)[0] + ' ' + datetime.now().strftime("%Y-%m-%d %H-%M-%S") + '.xlsx'
    writer = pd.ExcelWriter(xlsx)

    pd.DataFrame().to_excel(writer, sheet_name='data')
    isimple.video.metadata.save_to_excel(va.get_meta(), writer)

    pw = isimple.video.videodata.ProgressWindow(va)
    # todo: shouldn't have to call this explicitly, handle at VideoAnalyzer level.
    df = pd.DataFrame()

    while not va.done:  # todo: maybe do this at the VideoAnalyzer level.
        ct = va.get_next_frame()

        areas.append(va.areas())
        t.append(ct)

        df = pw.plot(t=t, areas=areas)
        pw.update()

    df.to_excel(
        writer, index=False, sheet_name='data',
    )
    writer.save()
    writer.close()

    pw.done = True
    pw.keepopen()
