import isimple
from isimple.video import demo

if __name__ == '__main__':
    isimple.update()

    demo(
        video='D:/temp/SIMPLE/dries.mp4',
        design='D:/temp/SIMPLE/dries.svg',
        timestep=20,
        height=0.153
    )
