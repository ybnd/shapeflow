import cv2
import os
import numpy as np
import matplotlib.pyplot as plt

# todo: for some reason, this approach produces different results on linux...
        # because we're using different images, duh!

DPI = 400
DPmm = 400 / 25.4

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

def crop_mask(mask: np.ndarray) -> (np.ndarray, np.ndarray):
    nz = np.nonzero(mask)
    r0 = nz[0].min()
    r1 = nz[0].max()
    c0 = nz[1].min()
    c1 = nz[1].max()
    cropped_mask = mask[r0:r1, c0:c1]
    return cropped_mask, np.array([r0,r1,c0,c1])

full = cv2.imread(os.path.join(os.getcwd(), "overlay.png"))

PM = cv2.imread(os.path.join(os.getcwd(), "PM.png"))
WLC = cv2.imread(os.path.join(os.getcwd(), "WLC.png"))
SLC = cv2.imread(os.path.join(os.getcwd(), "SLC.png"))

PM_mask = to_mask(PM, kernel)
WLC_mask = to_mask(WLC, kernel)
SLC_mask = to_mask(SLC, kernel)

PM_mask, p = crop_mask(PM_mask)
WLC_mask, w = crop_mask(WLC_mask)
SLC_mask, s = crop_mask(SLC_mask)

# masked = cv2.bitwise_and(full, full, mask = WLC_mask)
# plt.imshow(masked)
# plt.show()

# area = np.sum(masked > 0)

# Get frame
cap = cv2.VideoCapture(os.path.join(os.getcwd(), "video2.mp4"))
frameN = cap.get(cv2.CAP_PROP_FRAME_COUNT)
fps = cap.get(cv2.CAP_PROP_FPS)



# Copied from try_tk_canvas_rectangel.py
transform = np.array([
    [1.04249170e+00, - 1.48927386e-02, - 4.54861469e+02],
     [-4.64578847e-03,  1.04762530e+00, - 2.67719368e+02],
    [-3.09281044e-06, - 9.41138866e-06,  1.00000000e+00],
])

t = []
PM_volume = []
WLC_volume = []
SLC_volume = []

for f in range(int(frameN)):
    if not f%200:
        t.append(f / fps)
        # todo: should be faster if we only use the "minimal" image size per mask (lots of unneeded operations)
        cap.set(cv2.CAP_PROP_POS_FRAMES, f)
        ret, frame = cap.read()

        Y,X,C = full.shape
        image = cv2.warpPerspective(frame, transform, (X,Y))
        image = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)

        image_p = image[p[0]:p[1], p[2]:p[3]]
        image_w = image[w[0]:w[1], w[2]:w[3]]
        image_s = image[s[0]:s[1], s[2]:s[3]]

        frame_PM = cv2.bitwise_and(image_p, image_p, mask = PM_mask)
        frame_WLC = cv2.bitwise_and(image_w, image_w, mask = WLC_mask)
        frame_SLC = cv2.bitwise_and(image_s, image_s, mask = SLC_mask)

        from_blue = (90, 50, 50)
        to_blue = (110, 255, 255)

        from_red = (140, 5, 10)
        to_red = (180, 255, 255)

        mask = cv2.inRange(frame_PM, from_blue, to_blue)

        frame_PM2 = cv2.bitwise_and(frame_PM, frame_PM, mask = mask)

        gray = np.zeros((frame_PM2.shape[0], frame_PM2.shape[1]), frame_PM2.dtype)
        gray[:,:] = frame_PM2[:,:,2]

        PM_volume.append(np.sum(gray > 0) / DPmm ** 2 * 0.153)

        mask = cv2.inRange(frame_WLC, from_blue, to_blue)

        frame_PM2 = cv2.bitwise_and(frame_WLC, frame_WLC, mask = mask)

        gray = np.zeros((frame_PM2.shape[0], frame_PM2.shape[1]), frame_PM2.dtype)
        gray[:, :] = frame_PM2[:, :, 2]

        WLC_volume.append(np.sum(gray > 0) / DPmm ** 2 * 0.153)

        mask = cv2.inRange(frame_SLC, from_red, to_red)

        frame_PM2 = cv2.bitwise_and(frame_SLC, frame_SLC, mask = mask)

        gray = np.zeros((frame_PM2.shape[0], frame_PM2.shape[1]), frame_PM2.dtype)
        gray[:, :] = frame_PM2[:, :, 2]

        SLC_volume.append(np.sum(gray > 0) / DPmm ** 2 * 0.153)

plt.plot(t, PM_volume, label = 'PM')
plt.plot(t, WLC_volume, label = 'WLC')
plt.plot(t, SLC_volume, label = 'SLC')

plt.legend()
plt.title('Image processing - volume measurement')
plt.ylabel('Volume (uL)')
plt.xlabel('Time (s)')
plt.show()