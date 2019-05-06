import isimple
import argparse
from isimple.video.videodata import *
from datetime import datetime


parser = argparse.ArgumentParser()
parser.add_argument(
    'video', help='Path to video file', type=str
)
parser.add_argument(
    'design', help='Path to design file (.svg)', type=str
)
parser.add_argument(
    '-dt', help='Time interval in seconds', type=float, default=5
)
parser.add_argument(
    '-hc', help='Channel height in millimetres', type=float, default=0.153
)


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


if __name__ == '__main__':
    isimple.update()

    args = parser.parse_args()
    demo(args.video, args.design, args.dt, args.hc)





