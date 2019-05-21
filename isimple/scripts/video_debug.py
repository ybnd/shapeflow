import isimple
from isimple.video import video_analysis_demo

if __name__ == '__main__':
    isimple.update()

    video_analysis_demo(
        video='D:/temp/SIMPLE/pressure.mp4',
        design='D:/temp/SIMPLE/pressure.svg',
        timestep=20,
        height=0.153
    )
