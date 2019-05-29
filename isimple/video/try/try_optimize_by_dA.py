import numpy as np
from isimple.video.videodata import VideoAnalyzer
import scipy.optimize
import copy

import matplotlib.pyplot as plt


video = "D:/temp/SIMPLE/shuttle.mp4"
design = "D:/temp/SIMPLE/shuttle.svg"

va = VideoAnalyzer(video, design)
transform_og = copy.copy(va.transform)
area_og = copy.copy(np.sum(va.areas()))


def target(x):
    va.transform = np.array([x[0:3], x[3:6], x[6:9]])
    va.get_frame(500)
    areas = -np.sum(va.areas())
    return areas


IterPoints = 20
transforms = []
opt_areas = []

maxiters = 1+np.linspace(0, IterPoints-1, IterPoints)**2

for maxiter in maxiters:
    result = scipy.optimize.minimize(target, transform_og, method='Nelder-Mead', options={'maxiter': maxiter})
    x = result.x

    transforms.append(np.array([x[0:3], x[3:6], x[6:9]]))
    va.transform = np.array([x[0:3], x[3:6], x[6:9]])
    opt_areas.append(np.sum(va.areas()))


plt.figure()
plt.plot(maxiters, opt_areas)
plt.show()