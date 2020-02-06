import os, sys
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
    while not va.done:  # todo: do this at the VideoAnalyzer level!
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


def video_analysis_demo_jitter_transform(video, design, timestep, height, jitter_list):
    t = []
    areas = [[] for _ in jitter_list]

    va = isimple.video.videodata.VideoAnalyzer(
        video, design, dt=timestep, h=height
    )

    og_transform = va.transform

    va.reset()

    # alter the transform matrix by adding a specified jitter matrix

    xlsx = os.path.splitext(va.name)[0] + f' jitterD ' + datetime.now().strftime("%Y-%m-%d %H-%M-%S") + '.xlsx'
    writer = pd.ExcelWriter(xlsx)

    df = []

    # export metadata for jittered transforms
    for i, jitter in enumerate(jitter_list):
        va.transform = og_transform * (1+jitter)
        va.export_frame_overlay(f'{va.name} jitterD-{i}.png')
        isimple.video.metadata.save_to_excel(va.get_meta(), writer, sheet=f'metadata-jitterD-{i}')
        va.transform = og_transform

        df.append(pd.DataFrame())

    pw = isimple.video.videodata.ProgressWindow(va)
    # todo: shouldn't have to call this explicitly, handle at VideoAnalyzer level.

    while not va.done:  # todo: maybe do this at the VideoAnalyzer level.
        ct = va.get_next_frame()
        t.append(ct)
        for i, jitter in enumerate(jitter_list):
            va.transform = og_transform * (1+jitter)
            va.get_frame()
            areas[i].append(va.areas())

            df[i] = pw.plot(t=t, areas=areas[i])
            pw.update()

            va.transform = og_transform

        if not va.done:
            avg_df = pd.concat(df).mean(level=0)
            std_df = pd.concat(df).std(level=0)
            cv_df = std_df/avg_df

            avg_df.to_excel(
                writer, index=False, sheet_name=f'data-avg',
            )
            std_df.to_excel(
                writer, index=False, sheet_name=f'data-std',
            )
            cv_df.to_excel(
                writer, index=False, sheet_name=f'data-cv',
            )
            writer.save()
    writer.close()

    pw.done = True
    pw.close(False)

    # Reset transform to original and export .meta
    va.transform = og_transform
    va.export_metadata()

    sys.exit()

