import isimple
import argparse
from isimple.video import demo


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

if __name__ == '__main__':
    isimple.update()

    args = parser.parse_args()
    demo(args.video, args.design, args.dt, args.hc)





