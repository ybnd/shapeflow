from diskcache import Cache
import cv2
import os
import re
import time
import logging
import traceback
from typing import Tuple, List
import numpy as np
from OnionSVG import OnionSVG, check_svg

from isimple.utility.images import ckernel, crop_mask
from isimple.utility import describe_function


__CACHE_DIRECTORY__ = os.path.join(os.getcwd(), '.cache')
__CACHE_SIZE_LIMIT__ = 2 ** 32

logging.basicConfig(
    filename='.log', level=logging.DEBUG
)


class VideoFileTypeError(Exception):
    pass


class VideoAnalysisElement(object):  # todo: more descriptive name
    __default__ = {
    }

    def __init__(self, config: dict):
        self._config = self.handle_config(config)

    def handle_config(self, config: dict = None) -> dict:
        if config is None:
            config = {}

        # Gather __default__ from all parents
        __default__ = {}
        for base_class in self.__class__.__bases__:
            if hasattr(base_class, '__default__'):
                __default__.update(base_class.__default__)
        __default__.update(self.__default__)

        _config = {}
        for key, default in __default__.items():
            if key in config:
                _config[key] = config[key]
            else:
                _config[key] = default

        return _config

    def __getitem__(self, item):
        return self._config[item]


class VideoInterface(VideoAnalysisElement):
    """Interface to video files ~ OpenCV
    """
    __default__ = {
        'cache_dir': os.path.join(os.getcwd(), '.cache'),
        'cache_size_limit': 2 ** 32,  # cache size limit
    }

    def __init__(self, video_path, config: dict = None):
        super(VideoInterface, self).__init__(config)

        if not os.path.isfile(video_path):
            raise FileNotFoundError

        self.path = video_path
        self.name = video_path.split('\\')[-1].split('.png')[0]
        self._cache = None

        self._capture = cv2.VideoCapture(
            os.path.join(os.getcwd(), self.path)
        )  # todo: handle failure to open capture

        self.Nframes = int(self._capture.get(cv2.CAP_PROP_FRAME_COUNT))
        self.fps = self._capture.get(cv2.CAP_PROP_FPS)
        self.frame_number = int(self._capture.get(cv2.CAP_PROP_POS_FRAMES))

        if self.Nframes == 0:
            raise VideoFileTypeError

    def _get_key(self, method, *args, **kwargs) -> int:
        # key should be instance-independent to handle multithreading
        #  and caching between application runs
        #  i.e. hash __name__ instead of bound method
        return hash(f"{self.path} {describe_function(method)} {args} {kwargs}")

    def _set_position(self, frame_number: int):
        self._capture.set(cv2.CAP_PROP_POS_FRAMES, frame_number)
        self._get_position()

    def _get_position(self) -> int:
        self.frame_number = self._capture.get(cv2.CAP_PROP_POS_FRAMES)
        return self.frame_number

    def get_frame(self, frame_number: int = None,
                  to_hsv: bool = True, from_cache = False):
        key = self._get_key(self.get_frame, frame_number, to_hsv)
        # Check cache
        if key in self._cache:
            # Get frame from cache
            frame = self._cache.get(key)

            while isinstance(frame, str) and frame == 'in progress':
                # Some other thread is currently reading the same frame
                # Wait a bit and try to get from cache again
                time.sleep(0.01)  # todo: DiskCache-level events?
                frame = self._cache.get(key)

            return frame
        elif not from_cache:
            # Deposit a temporary entry into the cache
            self._cache.set(key, 'in progress')

            # Get frame from OpenCV capture
            if frame_number is None:
                frame_number = int(self.Nframes / 2)

            self._set_position(frame_number)
            ret, frame = self._capture.read()

            if ret:
                if to_hsv:
                    frame = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

                self._cache.set(key, frame)
                return frame
            else:
                return None  # todo: what do when no frame? cases?

    def __enter__(self):
        self._cache = Cache(
            directory=self['cache_dir'],
            size_limit=self['cache_size_limit'],
        )
        return self

    def __exit__(self, exc_type, exc_value, tb):
        self._cache.close()
        if exc_type is not None:
            return False
        else:
            return True


class VideoAnalyzer(VideoInterface):
    """Main video handling class
        * Load frames from video files
        * Load mask files
        * Load/save measurement metadata
    """

    __default__ = {
        'dt': 5,  # time interval in seconds
        'dpi': 400,  # DPI to render .svg at
        'render_dir': os.path.join(os.getcwd(), '.render'),
        'keep_renders': False,
        'transform': None,
    }

    def __init__(self, video_path: str, design_path: str, config: dict = None):
        super(VideoAnalyzer, self).__init__(video_path)

        self._config = self.handle_config(config)

        if not os.path.isfile(design_path):
            raise FileNotFoundError

        self._overlay, self._masks = self.handle_design(design_path)
        self._transform = Transform(self._config)

    def clear_renders(self):
        renders = [f for f in os.listdir(self['render_dir'])]
        for f in renders:
            os.remove(os.path.join(self['render_dir'], f))

    def handle_design(self, design_path) \
            -> Tuple[np.ndarray, List[VideoAnalysisElement]]:

        if not os.path.isdir(self['render_dir']):
            os.mkdir(self['render_dir'])
        else:
            self.clear_renders()

        check_svg(design_path)
        OnionSVG(design_path, dpi=self['dpi']).peel(
            'all', to=self['render_dir']
        )

        print("\n")

        overlay = cv2.imread(
            os.path.join(self['render_dir'], 'overlay.png')
        )

        files = os.listdir(self['render_dir'])
        files.remove('overlay.png')

        # todo: explain this stuff
        pattern = re.compile('(\d+)[?\-=_#/\\\ ]+([?\w\-=_#/\\\ ]+)')

        sorted_files = []
        matched = {}
        mismatched = []

        for path in files:
            name = os.path.splitext(path)[0]
            match = pattern.search(name)

            if match:
                matched.update(
                    {int(match.groups()[0]): path}
                )
            else:
                mismatched.append(path)

        for index in sorted(matched.keys()):
            sorted_files.append(matched[index])

        sorted_files = sorted_files + mismatched

        masks = []
        for path in sorted_files:
            masks.append(Mask(path, self, self._config))

        if not self['keep_renders']:
            self.clear_renders()

        return overlay, masks

    def get_frame(self, frame_number=None, do_transform=True, to_hsv=True):
        super(VideoAnalyzer, self).get_frame(frame_number, to_hsv)
        # transform
        if do_transform:
            pass

    def get_next_frame(self, to_hsv = True):
        pass

    def get_state_image(self):
        pass


class Transform(VideoAnalysisElement):
    """Handles coordinate transforms.
        Transform objects can point to a parent transform
        -- the transform is applied in sequence!
    """
    __default__ = {
        'transform': None
    }

    def __init__(self, config):
        super(Transform, self).__init__(config)


class Filter(VideoAnalysisElement):
    """Handles pixel filtering operations
    """
    pass


class HueRangeFilter(Filter):
    """Filters by a range of hues ~ HSV representation
    """
    pass


class Mask(VideoAnalysisElement):
    """Handles masks in the context of a video file
    """

    __default__ = {
        'render_dir': os.path.join(os.getcwd(), '.render'),
        'kernel': ckernel(7),  # mask smoothing kernel
    }

    def __init__(self, path: str, va: VideoAnalyzer, config: dict):
        super(Mask, self).__init__(config)
        self._va = va



class guiElement(object):
    """Abstract class for GUI elements
    """
    pass


class guiInteractiveMethod(guiElement):
    """GUI representation of an interactive method
    """
    pass


class guiWindow(object):
    """Abstract class for a GUI window
    """
    pass


class guiTransform(guiWindow):
    """A manual transform selection window
    """
    pass


class guiFilter(guiWindow):
    """A manual filter selection window
    """
    pass


class guiProgress(guiWindow):
    """A progress window
    """
    pass