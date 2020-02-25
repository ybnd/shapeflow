import os
import subprocess

script = '''
from isimple.scripts.video_gui import FileSelectWindow, demo

if __name__ == '__main__':
    fs = FileSelectWindow()
    v, d, t, h = fs.output
    demo(v, d, t, h)
'''

os.environ['PATH'] += os.pathsep + os.path.join(os.getcwd(), '.venv/Scripts')
subprocess.call(['.venv/Scripts/python', '-c', script])
