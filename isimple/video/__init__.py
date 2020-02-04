from isimple.video.videodata import *
from datetime import datetime


def demo(video, design, timestep, height): # todo: method name should be more descriptive
    t = []
    areas = []

    va = VideoAnalyzer(
        video, design, dt=timestep, h=height
    )
    va.reset()

    pw = ProgressWindow(va)

    df = pd.DataFrame()
    while not va.done:  # todo: do this at the VideoAnalyzer level!
        ct = va.get_next_frame()

        areas.append(va.areas())
        t.append(ct)

        df = pw.plot(t=t, areas=areas)
        pw.update()

    xlsx = os.path.splitext(
        pw.video.name)[0] + ' ' \
           + datetime.now().strftime("%Y-%m-%d %H-%M-%S") + '.xlsx'

    writer = pd.ExcelWriter(xlsx)
    df.to_excel(
        writer, index=False, sheet_name='data',
    )
    meta = va.get_meta()

    files = ['video', 'design']
    df_files = pd.DataFrame(
        [meta[k] for k in files], index=files, columns=['path']
    )
    coordinates = ['pt' + str(i) for i in range(4)]
    df_coordinates = pd.DataFrame(
        meta['coordinates'], index=coordinates, columns=['x', 'y']
    )
    df_transform = pd.DataFrame(meta['transform'])
    df_colors = pd.DataFrame(meta['colors']).transpose()

    df_files.to_excel(
        writer, header=False, sheet_name='metadata'
    )
    df_coordinates.to_excel(
        writer, startrow=3, index=True, sheet_name='metadata'
    )
    df_transform.to_excel(
        writer, startrow=3, startcol=4, sheet_name='metadata'
    )
    df_colors.to_excel(
        writer, startrow=9, sheet_name='metadata'
    )

    writer.save()
    writer.close()

    pw.done = True
    pw.keepopen()
