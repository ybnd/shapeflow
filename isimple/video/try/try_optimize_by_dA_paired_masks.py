import numpy as np
from isimple.video.videodata import VideoAnalyzer
import scipy.optimize
from scipy.spatial.distance import pdist, squareform

import copy

import matplotlib.pyplot as plt
import time

import sys
import cv2


video = "/home/ybnd/code/SIMPLE/data/shuttle.mp4"
design = "/home/ybnd/code/SIMPLE/data/shuttle.svg"

va = VideoAnalyzer(video, design, prompt_color=False, prompt_transform=False)


positions = []
for mask in va.masks:
    positions.append(mask.center)


positions = np.array(positions)
vdist = pdist(positions)
distance = squareform(vdist)

sdist = np.sort(distance, axis=1)