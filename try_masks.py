import cv2
import os
import numpy as np
import matplotlib.pyplot as plt

# todo: for some reason, this approach produces different results on linux...
        # because we're using different images, duh!

def ckernel(size):
    if not size%2: size = size-1
    index = int(size/2)

    # mask = np.zeros([size,size])
    y,x = np.ogrid[-index:size-index, -index:size-index]
    r = int(size/2)
    mask = x*x + y*y <= r*r
    array = np.zeros([size,size], dtype = np.uint8)
    array[mask] = 255
    return array

kernel = ckernel(7)

def to_mask(image, kernel):
    image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    ret, image = cv2.threshold(image, 200, 255, cv2.THRESH_BINARY)
    image = cv2.morphologyEx(image, cv2.MORPH_OPEN, kernel)
    return np.abs(np.subtract(np.array(image, dtype = np.uint8), 255))

def gray_to_mask(image, kernel):
    ret, image = cv2.threshold(image, 200, 255, cv2.THRESH_BINARY)
    image = cv2.morphologyEx(image, cv2.MORPH_OPEN, kernel)
    return np.abs(np.subtract(np.array(image, dtype=np.uint8), 255))

full = cv2.imread(os.path.join(os.getcwd(), "overlay.png"))

PM = cv2.imread(os.path.join(os.getcwd(), "PM.png"))
WLC = cv2.imread(os.path.join(os.getcwd(), "WLC.png"))
SLC = cv2.imread(os.path.join(os.getcwd(), "SLC.png"))

PM_mask = to_mask(PM, kernel)
WLC_mask = to_mask(WLC, kernel)
SLC_mask = to_mask(SLC, kernel)

masked = cv2.bitwise_and(full, full, mask = WLC_mask)

# plt.imshow(masked)
# plt.show()

# area = np.sum(masked > 0)

# Get frame
cap = cv2.VideoCapture(os.path.join(os.getcwd(), "video.mp4"))

frameN = cap.get(cv2.CAP_PROP_FRAME_COUNT)

cap.set(cv2.CAP_PROP_POS_FRAMES, int(frameN/4))
ret, frame = cap.read()

# Copied from try_tk_canvas_rectangel.py
transform = np.array([
    [-1.24008700e+00, - 1.47603451e-16,  1.73922202e+03],
     [6.58495362e-03, - 1.23467880e+00,  1.24087689e+03],
    [-1.07494466e-07,  1.00368835e-05,  1.00000000e+00],
])

Y,X,C = full.shape
image = cv2.warpPerspective(frame, transform, (X,Y))

frame_PM = cv2.bitwise_and(image, image, mask = PM_mask)
frame_WLC = cv2.bitwise_and(image, image, mask = WLC_mask)
frame_SLC = cv2.bitwise_and(image, image, mask = SLC_mask)

from_blue = (90, 50, 50)
to_blue = (110, 255, 255)

from_red = (140, 5, 10)
to_red = (180, 255, 255)

hsv = cv2.cvtColor(frame_PM, cv2.COLOR_BGR2HSV)
mask = cv2.inRange(hsv, from_blue, to_blue)

frame_PM2 = cv2.bitwise_and(hsv, hsv, mask = mask)

bgr = cv2.cvtColor(frame_PM2, cv2.COLOR_HSV2BGR)
gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)

area = np.sum(gray > 0)
print(area)

cv2.imshow('PM', gray)

hsv = cv2.cvtColor(frame_WLC, cv2.COLOR_BGR2HSV)
mask = cv2.inRange(hsv, from_blue, to_blue)

frame_PM2 = cv2.bitwise_and(hsv, hsv, mask = mask)

bgr = cv2.cvtColor(frame_PM2, cv2.COLOR_HSV2BGR)
gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)

area = np.sum(gray > 0)
print(area)

cv2.imshow('WLC', gray)

hsv = cv2.cvtColor(frame_SLC, cv2.COLOR_BGR2HSV)
mask = cv2.inRange(hsv, from_red, to_red)

frame_PM2 = cv2.bitwise_and(hsv, hsv, mask = mask)

bgr = cv2.cvtColor(frame_PM2, cv2.COLOR_HSV2BGR)
gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)

area = np.sum(gray > 0)
print(area)

cv2.imshow('SLC', gray)

cv2.waitKey()
