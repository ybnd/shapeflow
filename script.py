from source.videodata import *

import numpy as np
import matplotlib.pyplot as plt
import time

import asyncio
import threading

def start_loop(loop):
    asyncio.set_event_loop(loop)
    loop.run_forever()

__loop__ = asyncio.new_event_loop()
__thread__ = threading.Thread(target=start_loop, args=(__loop__,))

DPI = 400
DPmm = 400 / 25.4

t = []
areas = []

va = VideoAnalyzer("video2.mp4", "./overlay", dt = 5)
va.reset()


def playvid():
    while not va.done:
        ct = va.get_next_frame()

        if not va.done:
            areas.append(va.areas())
            t.append(ct)

            pw.plot(t = t, areas = areas)
            pw.update()

pw = ProgressWindow(va)

playvid()

pw.keepopen()


