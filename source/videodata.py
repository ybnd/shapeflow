import cv2
import os
import numpy as np
import matplotlib.pyplot as plt

from utils import timing
import time

from source.gui import *

DPI = 400               # todo: this is a workaround
DPmm = 400 / 25.4


def ckernel(size):
    if not size % 2: size = size - 1
    index = int(size / 2)

    y, x = np.ogrid[-index:size - index, -index:size - index]
    r = int(size / 2)
    mask = x * x + y * y <= r * r
    array = np.zeros([size, size], dtype=np.uint8)
    array[mask] = 255
    return array


def to_mask(image, kernel):
    image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    ret, image = cv2.threshold(image, 200, 255, cv2.THRESH_BINARY)
    image = cv2.morphologyEx(image, cv2.MORPH_OPEN, kernel)
    return np.abs(np.subtract(np.array(image, dtype=np.uint8), 255))


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
    return cropped_mask, np.array([r0, r1, c0, c1])


class VideoAnalyzer:
    __default_kernel__ = ckernel(7)
    __default_dt__ = 60

    def __init__(self, path, mask_folder, dt = None, kernel = None):
        self.path = path
        self.name = path.split('\\')[-1].split('.png')[0]
        self.mask_folder = mask_folder

        if kernel is None:
            self.kernel = self.__default_kernel__
        else:
            self.kernel = kernel

        if dt is None:
            self.dt = self.__default_dt__
        else:
            self.dt = dt

        self.transform = None
        self.shape = None

        self.previous_number = 1
        self.previous_frame = None
        self.frame = None
        self.done = False

        self.capture = cv2.VideoCapture(os.path.join(os.getcwd(), self.path))
        # todo: failure should be more verbose!
        self.frameN = int(self.capture.get(cv2.CAP_PROP_FRAME_COUNT))
        self.fps = self.capture.get(cv2.CAP_PROP_FPS)

        self.load_overlay()
        self.prompt_transform()

        self.masks = []
        self.colors = dict()

        self.load_masks()

    def load_overlay(self):
        self.overlay = cv2.imread(os.path.join(self.mask_folder, 'overlay.png'))

    def prompt_transform(self):
        OverlayAlignWindow(self)


    def load_masks(self):
        files = os.listdir(self.mask_folder)
        files.remove('overlay.png')

        for path in files:
            self.masks.append(Mask(self, os.path.join(self.mask_folder, path), kernel=self.kernel))


    def set_color(self, mask, color):
        tolerance = 10
        increment = 60


        repitition = 0

        for m in self.colors.keys():

            print(f"Distance of {abs(color[0] - self.colors[m][0])}")

            if abs(float(color[0]) - float(self.colors[m][0])) < tolerance and m != mask:
                repitition = repitition + 1

        self.colors.update(
            {mask: (color[0], 220, 255 - repitition * increment)}
        )

        print(f"Colors: {[self.colors[m] for m in self.colors.keys()]}")


    def get_state_image(self):
        state_image = np.zeros(self.frame.shape, dtype = np.uint8)

        for mask in self.masks:
            _, filter = mask.get_images()

            fullcolor = np.multiply(
                np.ones((filter.shape[0], filter.shape[1], 3)), self.colors[mask]
            )

            # filter = cv2.cvtColor(filter, cv2.COLOR_GRAY2RGB)
            # hsv_filter = cv2.cvtColor(filter, cv2.COLOR_RGB2HSV)

            mask_state = cv2.bitwise_and(fullcolor, fullcolor, mask = filter)

            state_image[
                mask.position[0]:mask.position[1],
                mask.position[2]:mask.position[3]
            ] = mask_state


        return state_image


    def warp(self, frame):
        return cv2.warpPerspective(frame, self.transform, (self.shape[1], self.shape[0]))


    def reset(self):
        self.previous_number = 0
        self.capture.set(cv2.CAP_PROP_POS_FRAMES, 1)


    def get_frame(self, number=None, do_warp = True, to_hsv=True):
        if number is None:
            number = int(self.frameN / 4)

        if self.previous_number != number:
            self.capture.set(cv2.CAP_PROP_POS_FRAMES, number)
            ret, self.frame = self.capture.read()

            if do_warp:
                self.frame = self.warp(self.frame)

            if to_hsv:
                self.frame = cv2.cvtColor(self.frame, cv2.COLOR_BGR2HSV)

            self.previous_number = number
            self.previous_frame = self.frame
        else:
            self.frame = self.previous_frame

        return self.frame


    def get_frame_at(self, position: float = 0.5, do_warp = True, to_hsv=True):
        number = int(self.frameN * position)
        return self.get_frame(number, do_warp, to_hsv)


    def get_next_frame(self, to_hsv = True):
        number = self.previous_number + int(self.dt * self.fps)

        if number > self.frameN:
            self.done = True
            self.frame = None
        else:
            self.get_frame(number, to_hsv)
            return float(number) / self.fps


    def areas(self, frame = None):
        if frame is None:
            frame = self.frame

        return [mask.area(frame) for mask in self.masks]


class Mask:
    __hue_radius__ = 15
    __sat_window__ = [50, 255]
    __val_window__ = [50, 255]

    def __init__(self, video, path, filter_color=None, kernel=ckernel(7)):
        self.video = video
        self.path = path
        self.name = path.split('\\')[-1].split('.png')[0]
        self.kernel = kernel

        self.full = to_mask(cv2.imread(path), self.kernel)
        self.video.shape = self.full.shape  # todo: should be the same for all files...
        self.partial, self.position = crop_mask(self.full)

        self.filter_from = np.array([90, 50, 50])
        self.filter_to = np.array([110, 255, 255])
        self.color = np.array([100, 255, 200])

        self.video.set_color(self, self.color)

        if filter_color is None:
            self.choose_color()

    def choose_color(self, color=None):
        if color is None:
            self.I = self.mask(self.video.get_frame())
            MaskFilterWindow(self)
        else:
            self.set_filter(color)

    def set_filter(self, color):
        hue = color[0]
        self.filter_from = np.array(
            [hue - self.__hue_radius__, self.__sat_window__[0], self.__val_window__[0]])
        self.filter_to = np.array(
            [hue + self.__hue_radius__, self.__sat_window__[1], self.__val_window__[1]])

        print(f"Color = {color}")

        self.video.set_color(self, color)

    def get_images(self):
        self.I = self.mask(self.video.frame)
        return (self.I, self.filter(self.I))

    def pick(self, coo):
        self.set_filter(self.I[coo.y,coo.x])


    def track(self, value):
        self.I = self.mask(self.video.get_frame(value))

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