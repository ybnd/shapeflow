import re
import warnings

import isimple.video.metadata as metadata
from isimple.video.analysis import *
from isimple.video.gui import *        # todo: would make more sense the other way around
from OnionSVG import OnionSVG, check_svg

DPI = 400               # todo: this is a workaround
DPmm = 400 / 25.4


def ckernel(size):
    """ Circular filter kernel """
    if not size % 2: size = size - 1
    index = int(size / 2)

    y, x = np.ogrid[-index:size - index, -index:size - index]
    r = int(size / 2)
    mask = x * x + y * y <= r * r
    array = np.zeros([size, size], dtype=np.uint8)
    array[mask] = 255
    return array


def to_mask(image, kernel):
    """ Convert a .png image to a binary mask """
    image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    ret, image = cv2.threshold(image, 254, 255, cv2.THRESH_BINARY)
    image = cv2.morphologyEx(image, cv2.MORPH_OPEN, kernel)

    # The binary threshold does not always map the same binary value to the center of the mask (should be the darker tone)
    # To circumvent this, we assume that the outer edge is not included in the mask (should be ok in normal cases)
    #   We want to end up with the mask as 255, the background as 0

    # Apparently that's not it, do the arithmetic in float & convert to uint8 afterwards!

    if image[0,0] == 255:
        return np.array(np.abs(np.subtract(255,np.array(image, dtype=np.float))), dtype = np.uint8)
    else:
        return image


def crop_mask(mask: np.ndarray) -> (np.ndarray, np.ndarray):
    """ Crop a binary mask image to its minimal size (to exclude unnecessary regions) """
    nz = np.nonzero(mask)
    row_0 = nz[0].min()
    row_1 = nz[0].max()
    col_0 = nz[1].min()
    col_1 = nz[1].max()
    cropped_mask = mask[row_0:row_1, col_0:col_1]
    return cropped_mask, np.array([row_0, row_1, col_0, col_1])


class VideoAnalyzer:
    """
        Main video handling class
    """

    __default_kernel__ = ckernel(7)
    __default_dt__ = 60
    __default_h__ = 0.153

    __render_folder__ = os.path.join(os.getcwd(), '.render')

    __overlay_DPI__ = 400

    def __init__(self, video_path, overlay_path, dt = None, h = None, kernel = None):
        self.path = video_path
        self.name = video_path.split('\\')[-1].split('.png')[0]
        self.overlay_path = overlay_path

        if kernel is None:
            self.kernel = self.__default_kernel__
        else:
            self.kernel = kernel

        if dt is None:
            self.dt = self.__default_dt__
        elif dt == "all":
            self.dt = None
        else:
            self.dt = dt

        if h is None:
            self.h = self.__default_h__
        else:
            self.h = h

        self.transform = np.eye(3)
        self.coordinates = None
        self.order = (0,1,2,3)
        self.shape = None

        self.number = 1
        self.previous_frame = None
        self.frame = None
        self.done = False

        self.masks = []
        self.colors = dict()
        self.plot_colors = dict()

        self.capture = cv2.VideoCapture(os.path.join(os.getcwd(), self.path))
        # todo: failure should be more verbose!
        self.frameN = int(self.capture.get(cv2.CAP_PROP_FRAME_COUNT))
        self.fps = self.capture.get(cv2.CAP_PROP_FPS)

        self.check_files()

        self.render_svg()
        self.load_overlay()

        self.import_metadata()
        self.prompt_transform()

        self.load_masks()
        self.export_metadata()

    def check_files(self):
        """ Check that the files exist and are of the correct type """
        check_svg(self.overlay_path)
        ok,_ = self.capture.read()

        if not ok:
            raise IOError('Invalid video file.')


    def render_svg(self):
        """ Render out the .svg design file. """

        if not os.path.isdir(self.__render_folder__):
            os.mkdir(self.__render_folder__)
        else:
            fl = [f for f in os.listdir(self.__render_folder__)]
            for f in fl: os.remove(os.path.join(self.__render_folder__, f))

        OnionSVG(
            self.overlay_path,
            dpi = self.__overlay_DPI__
        ).peel('all', to = self.__render_folder__)

        print("\n")

    def load_overlay(self):
        """ Load the rendered overlay image. """
        self.overlay = cv2.imread(os.path.join(self.__render_folder__, 'overlay.png'))

    def prompt_transform(self):
        """ Open the overlay transform selection window. """
        OverlayAlignWindow(self)

    def load_masks(self):
        """ Load the rendered mask images. """
        files = os.listdir(self.__render_folder__)
        files.remove('overlay.png')

        # todo: sort! ~ '(\d+)[?\-=_#/\\\ ]+([?\w\-=_#/\\\ ]+)'

        pattern = re.compile('(\d+)[?\-=_#/\\\ ]+([?\w\-=_#/\\\ ]+)')

        sorted_files = []
        matched = {}
        mismatched = []

        for path in files:
            name = os.path.splitext(path)[0]
            match = pattern.search(name)

            if match:
                matched.update(
                    {int(match.groups()[0]):path}
                )
            else:
                mismatched.append(path)

        for index in sorted(matched.keys()):
            sorted_files.append(matched[index])

        sorted_files = sorted_files + mismatched

        for path in sorted_files:
            self.masks.append(Mask(self, os.path.join(self.__render_folder__, path), kernel=self.kernel))

    def set_as_plot_color(self, mask, color):
        """ Set filtering color as plot color & space colors for readable plot """
        tolerance = 15
        increment = 60

        repetition = 0

        for m in self.plot_colors.keys():
            if abs(float(color[0]) - float(self.plot_colors[m][0])) < tolerance  and m != mask:
                repetition = repetition + 1


        self.plot_colors.update(
            {mask: (color[0], 220, 255 - repetition * increment)}
        )

        # print(f"Colors: {[self.colors[m] for m in self.colors.keys()]}")

    def get_state_image(self):
        """ Generate a 'state' image for the current frame.
                i.e.: show the detected regions for each mask (in the corresponding filtering hue) on the overlay image.
        """
        if self.frame is not None:
            state_image = np.zeros(self.frame.shape, dtype=np.uint8)

            for mask in self.masks:
                _, filter = mask.get_images()

                full = np.ones((filter.shape[0], filter.shape[1], 3), dtype=np.uint8)

                fullcolor = np.multiply(
                    full, self.plot_colors[mask]
                )

                mask_state = cv2.bitwise_and(fullcolor, fullcolor, mask = filter)

                state_image[
                    mask.position[0]:mask.position[1],
                    mask.position[2]:mask.position[3]
                ] = state_image[
                    mask.position[0]:mask.position[1],
                    mask.position[2]:mask.position[3]
                ] + mask_state

                state_image = cv2.cvtColor(state_image, cv2.COLOR_HSV2BGR)
                state_image[state_image == 0] = 255

                state_image = cv2.addWeighted(self.overlay, 0.05, state_image, 1-0.05, 0, state_image)
                state_image = cv2.cvtColor(state_image, cv2.COLOR_BGR2HSV)

            return state_image

    def warp(self, frame):
        """ Apply a perspective transform. """
        return cv2.warpPerspective(frame, self.transform, (self.shape[1], self.shape[0]))

    def reset(self):
        """ Reset position in the video file. """
        self.number = 0
        self.capture.set(cv2.CAP_PROP_POS_FRAMES, 1)

    def get_frame(self, number=None, do_warp = True, to_hsv=True):
        """ Get a specific frame from the video file. """
        if number is None:
            if self.number is None:
                self.number = int(self.frameN / 4)
            number = self.number

        # if self.number != number:
        self.capture.set(cv2.CAP_PROP_POS_FRAMES, number)
        ret, self.frame = self.capture.read()

        if self.frame is not None and ret:
            if to_hsv:
                try:
                    frame = cv2.cvtColor(self.frame, cv2.COLOR_BGR2HSV)
                except cv2.error as e:
                    warnings.warn(str(e), stacklevel=3)
                    frame = self.previous_frame

                self.frame = frame


            if do_warp:
                self.raw_frame = self.frame.copy()
                self.frame = self.warp(self.frame)

            self.number = number
            self.previous_frame = self.frame
            # else:
                # There's no way to know if previous frame was warped or not!!
                # self.frame = self.previous_frame

            return self.frame

    def get_frame_at(self, position: float = 0.5, do_warp = True, to_hsv=True):
        """ Get the frame at a relative position ~ [0,1] """
        number = int(self.frameN * position)
        return self.get_frame(number, do_warp, to_hsv)

    def get_next_frame(self, to_hsv = True):
        """ Advance to the next frame. """
        if self.dt is not None:
            number = self.number + int(self.dt * self.fps)
        else:
            number = self.number + 1

        if number >= self.frameN:
            self.done = True
            self.frame = None
        else:
            self.get_frame(number, to_hsv)
            if self.frame is None:
                self.done = True
                return None
            else:
                return float(number) / self.fps

    def areas(self, frame = None):
        """ Calculate the areas for all of the masks. """  # todo: abstract away from VideoAnalyzer
        if frame is None:
            frame = self.frame

        return [mask.area(frame) for mask in self.masks]

    def export_metadata(self):
        colors = {
            mask.name: {'from': mask.filter_from.tolist(), 'to': mask.filter_to.tolist()}
            for mask in self.masks
        }

        metadata.save(self.path, self.overlay_path, self.coordinates, self.transform.tolist(),
                      self.order, colors)

    def import_metadata(self):
        meta = metadata.load(self.path)

        if meta is not None:
            self.transform = np.array(meta['transform'])
            self.colors = meta['colors']
            self.order = meta['order']
            self.coordinates = meta['coordinates']

            for mask in self.colors.keys():
                for color in self.colors[mask].keys():
                    self.colors[mask][color] = np.array(self.colors[mask][color])

            print(f"Loaded metadata from {os.path.splitext(self.path)[0]+'.meta'}")

class Mask:

    """
        Video mask object.
    """

    __hue_radius__ = 10             # todo: better to save filter interval like this...
    __sat_window__ = [50, 255]
    __val_window__ = [50, 255]

    def __init__(self, video, path, kernel=ckernel(7)):
        self.video = video
        self.path = path

        pattern = re.compile('(\d+)[?\-=_#/\\\ ]+([?\w\-=_#/\\\ ]+)')
        fullname = os.path.splitext(os.path.basename(path))[0]
        self.name = pattern.search(fullname).groups()[1].strip()

        self.kernel = kernel

        self.full = to_mask(cv2.imread(path), self.kernel)
        self.video.shape = self.full.shape  # todo: should be the same for all files...
        self.partial, self.position = crop_mask(self.full)

        if self.name in self.video.colors:
            # Try to load color from metadata file
            self.filter_from = self.video.colors[self.name]['from']
            self.filter_to = self.video.colors[self.name]['to']
        else:
            # Default to blue
            self.filter_from = np.array([90, 50, 50])
            self.filter_to = np.array([110, 255, 255])

        self.color = np.array(
            [np.mean([self.filter_from[0], self.filter_to[0]]), 255, 200]
        )

        self.video.set_as_plot_color(self, self.color)

        self.choose_color()

    def choose_color(self, color=None):
        """ Choose a ue to filter at. """
        if color is None:
            frame = self.video.get_frame(do_warp = True)
            self.I = self.mask(frame)
            MaskFilterWindow(self)
        else:
            self.set_filter(color)

    def set_filter(self, color):
        """ Set the filtering hue. """
        hue = color[0]
        self.filter_from = np.array(
            [hue - self.__hue_radius__, self.__sat_window__[0], self.__val_window__[0]])
        self.filter_to = np.array(
            [hue + self.__hue_radius__, self.__sat_window__[1], self.__val_window__[1]])

        self.video.set_as_plot_color(self, color)

    def get_images(self):
        """ Return masked & filtered images. """
        self.I = self.mask(self.video.frame)
        return self.I, self.filter(self.I)

    def pick(self, coo):
        """ Callback - set filtering hue. """
        self.set_filter(self.I[coo.y,coo.x])

    def track(self, value):
        """ Get a specific frame from the video (callback for UI scrollbar). """
        self.I = self.mask(self.video.get_frame(value))

    def filter(self, image):
        """ Filter an image with the current filter. """
        if image is not None:
            filtermask = cv2.inRange(image, self.filter_from, self.filter_to)
            # todo: some kind of plugin functionality to do more involved filtering?
              # i.e.: startup option to set a self._filter method (image -> image)
            return filtermask

    def mask(self, image, do_crop = True):
        """ Mask off an image. """
        if image is not None:
            if do_crop:
                partial_image = image[
                                self.position[0]:self.position[1],
                                self.position[2]:self.position[3],
                                ].copy()
            else:
                partial_image = image

            frame = cv2.bitwise_and(partial_image, partial_image, mask=self.partial)

            return frame

    def mask_filter(self, image):
        """ Mask & filter an image. """
        frame = self.mask(image)
        filtered =  self.filter(frame)

        return filtered

    def area(self, image):
        """ Calculate the detected area in the masked & filtered image. """ # todo: abstract away form Mask
        return area_pixelsum(self.mask_filter(image))

