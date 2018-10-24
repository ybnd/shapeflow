import cv2
import os
import numpy as np
import matplotlib.pyplot as plt

from utils import timing
import time

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

class Series:
    def __init__(self, path, mask_folder, transform, kernel = ckernel(7)):
        self.path = path
        self.name = path.split('\\')[-1].split('.png')[0]

        self.mask_folder = mask_folder
        self.transform = transform
        self.kernel = kernel
        self.shape = None

        self.previous_number = None
        self.previous_frame = None

        self.capture = cv2.VideoCapture(os.path.join(os.getcwd(), self.path))
            # todo: failure should be more verbose!
        self.frameN = int(self.capture.get(cv2.CAP_PROP_FRAME_COUNT))
        self.fps = self.capture.get(cv2.CAP_PROP_FPS)

        self.masks = []
        self.load_masks()

    def load_masks(self):
        files = os.listdir(self.mask_folder)
        files.remove('overlay.png')

        for path in files:
            self.masks.append(Mask(self, os.path.join(self.mask_folder, path), kernel = self.kernel))

    @timing
    def warp(self, frame):
        return cv2.warpPerspective(frame, self.transform, (self.shape[1], self.shape[0]))

    @timing
    def load_frame(self, number = None, to_hsv = True):
        if number is None:
            number = int(self.frameN / 4)

        if self.previous_number != number:
            self.capture.set(cv2.CAP_PROP_POS_FRAMES, number)
            ret, frame = self.capture.read()

            frame = self.warp(frame)

            if to_hsv:
                frame = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

            self.previous_number = number
            self.previous_frame = frame
        else:
            frame = self.previous_frame

        return frame

    @timing
    def areas(self):
        return [mask.area(frame) for mask in self.masks]



class Mask:
    __hue_radius__ = 15
    __sat_window__ = [50, 255]
    __val_window__ = [50, 255]

    def __init__(self, series, path, filter_color = None, kernel = ckernel(7)):
        self.series = series
        self.path = path
        self.name = path.split('\\')[-1].split('.png')[0]
        self.kernel = kernel

        self.full = to_mask(cv2.imread(path), self.kernel)
        self.series.shape = self.full.shape # todo: should be the same for all files...
        self.partial, self.position = crop_mask(self.full)

        self.filter_from = np.array([90,50,50])
        self.filter_to = np.array([110,255,255])

        if filter_color is None:
            self.choose_color()

    def choose_color(self, color = None):
        if color is None:
            image = self.series.load_frame()
            self.I = self.mask(image)

            self.window = f"Choose a filtering hue... (press any key to commit)"
            self.filtered_window = f"Filter output"
            cv2.namedWindow(self.filtered_window, cv2.WINDOW_KEEPRATIO)
            cv2.namedWindow(self.window, cv2.WINDOW_KEEPRATIO)
            cv2.setMouseCallback(self.window, self.pick)
            cv2.createTrackbar('Frame', self.window, int(self.series.frameN / 4), self.series.frameN, self.track)
            cv2.imshow(self.window, cv2.cvtColor(self.I, cv2.COLOR_HSV2BGR))
            cv2.imshow(self.filtered_window, self.filter(self.I))
            cv2.waitKey()

            cv2.destroyAllWindows()
        else:
            self.set_filter(color)

    def set_filter(self, color):
        hue = color[0]
        self.filter_from = np.array([hue - self.__hue_radius__, self.__sat_window__[0], self.__val_window__[0]])
        self.filter_to = np.array([hue + self.__hue_radius__, self.__sat_window__[1], self.__val_window__[1]])

    def pick(self, event, x, y, flags, param):
        if event == cv2.EVENT_LBUTTONDOWN:
            color_HSV = self.I[y,x]
            color_RGB = cv2.cvtColor(np.array([[color_HSV]]), cv2.COLOR_HSV2RGB)[0,0]

            print(f"Picked color: HSV:{color_HSV} --> RGB:{color_RGB}")

            self.set_filter(color_HSV)
            print(f"Filter set to: {self.filter_from} -- {self.filter_to}")

            cv2.imshow(self.filtered_window, self.filter(self.I))

    def track(self, value):
        self.I = self.mask(self.series.load_frame(value))
        cv2.imshow(self.window, cv2.cvtColor(self.I, cv2.COLOR_HSV2BGR))
        cv2.imshow(self.filtered_window, self.filter(self.I))

    def filter(self, image):
        filtermask = cv2.inRange(image, self.filter_from, self.filter_to)
        return filtermask

    def mask(self, image):
        partial_image = image[
                        self.position[0]:self.position[1],
                        self.position[2]:self.position[3],
                        ].copy()

        frame = cv2.bitwise_and(partial_image, partial_image, mask=self.partial)

        return frame

    def mask_filter(self, image):
        frame = self.mask(image)
        return self.filter(frame)

    def area(self, image):
        return np.sum(self.mask_filter(image) > 1)


# Make Series instance

transform = np.array([
    [1.04249170e+00, - 1.48927386e-02, - 4.54861469e+02],
    [-4.64578847e-03,  1.04762530e+00, - 2.67719368e+02],
    [-3.09281044e-06, - 9.41138866e-06,  1.00000000e+00],
])

s = Series("video2.mp4", "./overlay", transform)

areas = []
t = []

t0 = time.time()

for f in range(int(s.frameN)):
    if not f%30*240:
        t.append(f / s.fps)
        frame = s.load_frame(f)     # takes about 0.2 - 0.3 s per frame!,
                                        # .avi is ~ 2-3 times worse
                                        # .mkv is about the same
        areas.append(s.areas())     # takes about 0.002 s per frame.

total = time.time() - t0
print(f"\n \n Total elapsed time: {total} s.")

areas = np.transpose(np.array(areas))

for i, curve in enumerate(areas):
    plt.plot(t, curve / DPmm **2 * 0.153, label = s.masks[i].name)

plt.legend()
plt.title('Image processing - volume measurement')
plt.ylabel('Volume (uL)')
plt.xlabel('Time (s)')
plt.show()



