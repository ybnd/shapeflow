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

t = []
areas = []

va = VideoAnalyzer("video2.mp4", "shuttle_overlay.svg", dt = 5)
va.reset()

pw = ProgressWindow(va)

while not va.done:
    ct = va.get_next_frame()

    if not va.done:
        areas.append(va.areas())
        t.append(ct)

        pw.plot(t=t, areas=areas)
        pw.update()

pw.keepopen()


