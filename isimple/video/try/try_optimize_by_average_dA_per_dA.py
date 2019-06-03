import numpy as np
from isimple.video.videodata import VideoAnalyzer
import scipy.optimize
import copy

import matplotlib.pyplot as plt
import time

import sys
import cv2


video = "D:/temp/SIMPLE/shuttle.mp4"
design = "D:/temp/SIMPLE/shuttle.svg"

va = VideoAnalyzer(video, design, prompt_color=False, prompt_transform=False)  # todo: "accept" metadata instead of showing screens
print('\n')

transform_og = copy.copy(va.transform)

area_og = copy.copy(np.sum(va.areas(va.get_frame_at(0.5))))

Nf = va.number
frames = [ va.get_frame_at(i, do_warp=False) for i in [0.5] ]

# Optimizing for all masks at once is actually more robust since it wont get into the 'just zoom in all the way'
# territory since the geometry & colors remain important


def target(x, args):
    va_opt = args[0]
    frames_opt = args[1]

    # transform = np.array([x[0:3], x[3:6], x[6:9]])
    transform = np.array([x[0:3], x[3:6], [0, 0, 1]])

    area_ratio = 0
    A = []

    # va.get_frame(do_warp=False)
    for frame in frames_opt:
        fr = cv2.warpPerspective(frame, transform, (va_opt.shape[1], va_opt.shape[0]))
        for mask in va_opt.masks:
            A.append(mask.neg_area(fr) / (mask.area(fr)+1))

    area_ratio = np.mean(A)

    sys.stdout.write(
        '\r' + f"T(0,0) = {transform[0, 0]}, avg dA = {area_ratio}"
    )


    # total_area = 0
    # for frame in frames:
    #     total_area -= np.sum(va.areas(va.warp(frame)))

    sys.stdout.flush()

    return area_ratio


IterPoints = 3
transforms = []
opt_areas = []
dts = []

maxiters = 1+np.linspace(0, IterPoints-1, IterPoints)**2

maxiter = 5

t = time.time()
result = scipy.optimize.minimize(
    target, transform_og.tolist(), [va, frames],
    method='Powell', options={'maxiter': maxiter})
x = result.x

# transforms.append(np.array([x[0:3], x[3:6], x[6:9]]))
# va.transform = np.array([x[0:3], x[3:6], x[6:9]])
transforms.append(np.array([x[0:3], x[3:6], [0, 0, 1]]))
va.transform = np.array([x[0:3], x[3:6], [0, 0, 1]])

opt_areas.append(np.sum(va.areas()))

dt = time.time() - t

print(f" Success: {result.success} after {result.nit}/{maxiter} iterations in {dt} seconds")
dts.append(dt)



# plt.figure()
# plt.plot(maxiters, transforms)
# plt.show()


# print(dts)

va.transform = transform_og
plt.figure()
va.get_frame_at(0.5, to_hsv=False)
plt.imshow(va.get_overlayed_frame())

va.transform = transforms[0]
plt.figure()
va.get_frame_at(0.5, to_hsv=False)
plt.imshow(va.get_overlayed_frame())

plt.show()

print(f"Transform: {transforms[0]}")

print('Done.')
