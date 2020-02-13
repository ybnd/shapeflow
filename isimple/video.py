from diskcache import Cache
import cv2
import os
import re
import time
import logging
from typing import Tuple, List, Optional
import numpy as np
from OnionSVG import OnionSVG, check_svg
import abc
import threading
from _collections import defaultdict

from isimple.maths.images import ckernel, to_mask, crop_mask
from isimple.util import describe_function
from isimple.gui import guiPane


__CACHE_DIRECTORY__ = os.path.join(os.getcwd(), '.cache')
__CACHE_SIZE_LIMIT__ = 2 ** 32

logging.basicConfig(
    filename='.log', level=logging.DEBUG
)


class VideoFileTypeError(Exception):
    pass


class VideoAnalysisElement(abc.ABC):  # todo: more descriptive name
    __default__: dict
    __default__ = {                  # todo: interface with isimple.meta
    }

    def __init__(self, config):
        self._config = self.handle_config(config)

    def handle_config(self, config: dict = None) -> dict:
        if config is None:
            config = {}

        # Gather default config from all parents
        default_config: dict = {}
        for base_class in self.__class__.__bases__:
            if hasattr(base_class, '__default__'):
                default_config.update(base_class.__default__)  #type: ignore
        default_config.update(self.__default__)

        _config = {}
        for key, default in default_config.items():
            if key in config:
                _config[key] = config[key]
            else:
                _config[key] = default
        return _config

    def __getattr__(self, item):
        """Get attribute value from self._config
        """  # todo: interface with metadata -> should raise an exception if unexpected attribute is got
        return self._config[item]

    def __call__(self, frame: np.ndarray) -> np.ndarray:
        raise NotImplementedError


class VideoFileHandler(VideoAnalysisElement):
    """Interface to video files ~ OpenCV
    """
    _cache: Optional[Cache]
    _background: Optional[threading.Thread]

    cache_dir: str
    cache_size_limit: int
    background_caching: bool

    __default__ = {
        'cache_dir': os.path.join(os.getcwd(), '.cache'),
        'cache_size_limit': 2 ** 32,                        # cache size limit
        'background_caching': False,                        # True -> start background caching thread along with cache
    }

    def __init__(self, video_path, config: dict = None):
        super(VideoFileHandler, self).__init__(config)

        if not os.path.isfile(video_path):
            raise FileNotFoundError

        self.path = video_path
        self.name = video_path.split('\\')[-1].split('.png')[0]
        self._cache = None
        self._background = None

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

    def read_frame(self, frame_number: int = None,
                   to_hsv: bool = True, from_cache = False):
        if frame_number is None:
            frame_number = self.frame_number

        key = self._get_key(self.read_frame, frame_number, to_hsv)
        # Check cache
        if self._cache is not None:
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

    def __enter__(self):
        self._cache = Cache(
            directory=self.cache_dir,
            size_limit=self.cache_size_limit,
        )
        if self.background_caching:
            pass  # todo: can start caching frames in background thread here

        return self

    def __exit__(self, exc_type, exc_value, tb):
        self._cache.close()

        if self._background is not None and self._background.is_alive():
            pass    # todo: can stop background thread here (gracefully)
                    #        ...also: self._background.is_alive() doesn't recognize self...

        if exc_type is not None:
            return False
        else:
            return True


class Transform(VideoAnalysisElement):
    """Handles coordinate transforms.
    """
    _shape: tuple
    _transform: np.ndarray

    transform_matrix: np.ndarray

    __default__ = {
        'transform_matrix': None
    }

    def __init__(self, shape, config):
        super(Transform, self).__init__(config)
        self._shape = shape

        self._transfrom = None
        if self.transform_matrix is not None:
            self.set(self.transform_matrix)
        else:
            self.set(np.eye(3))

    def set(self, transform: np.ndarray):
        """Set the transform matrix
        """
        raise NotImplementedError

    def estimate(self, coordinates):
        """Estimate the transform matrix from a set of coordinates
            coordinates should correspond to the corners of the outline of
            the design, ordered from the bottom left to the top right
        """
        raise NotImplementedError

    def __call__(self, img: np.ndarray) -> np.ndarray:
        """Transform a frame.
            Writes to the provided variable!
            If caller needs the original value, they should copy explicitly
        """
        raise NotImplementedError


class IdentityTransform(Transform):
    """Looks like a Transform, but doesn't transform
    """

    def set(self, transform: np.ndarray):
        pass

    def estimate(self, coordinates):
        pass

    def __call__(self, img: np.ndarray) -> np.ndarray:
        return img


class PerspectiveTransform(Transform):
    def set(self, transform: np.ndarray):
        pass

    def estimate(self, coordinates):
        # todo: sanity check the coordinates!
        #        * array size
        #        * ensure bottom left to top right order
        # todo: corner order should be handled by coordinates
        #        ordered @ gui if needed, supplied in the correct order
        self.set(
            cv2.getPerspectiveTransform(
                np.float32(coordinates),
                np.float32(
                    np.array(  # selection rectangle: bottom left to top right
                        [
                            [0, self._shape[0]],
                            [0, 0],
                            [self._shape[1], 0],
                            [self._shape[1], self._shape[0]]
                        ]
                    )
                )
            )
        )   # todo: this is messy :(

    def __call__(self, frame: np.ndarray) -> np.ndarray:
        return cv2.warpPerspective(
            frame, self._transform, self._shape
        )


class Filter(VideoAnalysisElement):
    """Handles pixel filtering operations
    """
    def __init__(self, config: dict):
        super(Filter, self).__init__(config)

    @abc.abstractmethod
    def mean_color(self) -> np.ndarray:  # todo: add custom np.ndarray type 'hsvcolor'
        raise NotImplementedError

    @abc.abstractmethod
    def __call__(self, image: np.ndarray) -> np.ndarray:  # todo: add custom np.ndarray type 'image'
        raise NotImplementedError


class HsvRangeFilter(Filter):
    """Filters by a range of hues ~ HSV representation
    """
    __default__ = {
        'hue_radius': 10,           # Radius to determine range from one color
        'sat_window': [50, 255],
        'val_window': [50, 255],
        'c0': [90, 50, 50],         # Start of filtering range (in HSV space)
        'c1':   [110, 255, 255],    # End of filtering range (in HSV space)
    }

    def __init__(self, config: dict):
        super(HsvRangeFilter, self).__init__(config)

    def mean_color(self) -> np.ndarray:
        # todo: S and V are arbitrary for now
        return np.array([np.mean(self.c0[0], self.c1[0]), 255, 200])

    def set_filter(self, clr):
        hue = clr[0]
        self.c0 = np.array([
            hue - self.hue_rad, self.sat_window[0], self.val_window[0]
        ])
        self.c1 = np.array([
            hue - self.hue_rad, self.sat_window[1], self.val_window[1]
        ])  # todo: plot color was set from here originally, but Filter shouldn't care about that

    def __call__(self, img: np.ndarray) -> np.ndarray:
        return cv2.inRange(img, self.c0, self.c1, img)


class Mask(VideoAnalysisElement):
    """Handles masks in the context of a video file
    """

    __default__ = {
        'render_dir': os.path.join(os.getcwd(), '.render'),
        'kernel': ckernel(7),   # mask smoothing kernel
    }

    def __init__(self, path: str, config: dict = None):
        super(Mask, self).__init__(config)
        self._path = path
        self.name = os.path.splitext(os.path.basename(path))[0]

        # todo: explain this!
        pattern = re.compile('(\d+)[?\-=_#/\\\ ]+([?\w\-=_#/\\\ ]+)')
        match = pattern.search(self.name)
        if match:
            self.name = match.groups()[1].strip()


        self._full = to_mask(cv2.imread(path), self.kernel)
        self._part, self._rect, self._center = crop_mask(self._full)

    def __call__(self, img: np.ndarray) -> np.ndarray:
        """Mask an image.
            Writes to the provided variable!
            If caller needs the original value, they should copy explicitly
        """

        img = self._crop(img)
        return cv2.bitwise_and(img, img, mask=self._part)


    def _crop(self, img: np.ndarray) -> np.ndarray:
        """Crop an image to fit self._part
            Writes to the provided variable!
            If caller needs the original value, they should copy explicitly
        """
        return img[self._rect[0]:self._rect[1], self._rect[2]:self._rect[3]]


class DesignFileHandler(VideoAnalysisElement):
    _overlay: np.ndarray
    _masks: List[Mask]

    dpi: int
    render_dir: str
    keep_renders: bool

    __default__ = {
        'dpi': 400,  # DPI to render .svg at
        'render_dir': os.path.join(os.getcwd(), '.render'),
        'keep_renders': False,
    }

    def __init__(self, path: str, config: dict = None):
        super(DesignFileHandler, self).__init__(config)

        if not os.path.isfile(path):
            raise FileNotFoundError

        self._path = path
        self._overlay, self._masks = self._handle_design(self._path)
        self._shape = self._overlay.shape  # todo: all Transform objects need to know about this

    def _clear_renders(self):
        renders = [f for f in os.listdir(self.render_dir)]
        for f in renders:
            os.remove(os.path.join(self.render_dir, f))

    def _handle_design(self, design_path) \
            -> Tuple[np.ndarray, List[Mask]]:

        if not os.path.isdir(self.render_dir):
            os.mkdir(self.render_dir)
        else:
            self._clear_renders()

        check_svg(design_path)
        OnionSVG(design_path, dpi=self.dpi).peel(
            'all', to=self.render_dir
        )

        print("\n")

        overlay = cv2.imread(
            os.path.join(self.render_dir, 'overlay.png')
        )

        files = os.listdir(self.render_dir)
        files.remove('overlay.png')

        # Catch file names of numbered layers
        pattern = re.compile('(\d+)[?\-=_#/\\\ ]+([?\w\-=_#/\\\ ]+)')

        sorted_files = []
        matched = {}
        mismatched = []

        for path in files:
            match = pattern.search(os.path.splitext(path)[0])
            path = os.path.join(self.render_dir, path)

            if match:
                matched.update(  # numbered layer
                    {int(match.groups()[0]): path}  # keep track of index
                )
            else:
                mismatched.append(path)  # not a numbered layer

        # Sort numbered layers
        for index in sorted(matched.keys()):
            sorted_files.append(matched[index])

        # Append unnumbered layers to the end of the list
        sorted_files = sorted_files + mismatched

        masks = []
        for path in sorted_files:
            masks.append(Mask(path, self._config))

        if not self.keep_renders:
            self._clear_renders()

        return overlay, masks

    @property
    def shape(self):
        return self._shape


class VideoAnalysis(VideoAnalysisElement):
    _config: dict
    _elements: List[VideoAnalysisElement]
    _element_types: dict = {
        'element': {
            'type': VideoAnalysisElement
        }
    }

    def _add_elements(self, elements: List[VideoAnalysisElement]):
        """Add VideoAnalysisElement instances to VideoAnalyzer
        """
        for e in elements:
            if True:   # todo: add sanity check here
                self._elements.append(e)

    def get_element(self, element, type):
        if element in self._element_types:
            if type in self._element_types[element]:
                return self._element_types[element][type]
            else:
                raise ValueError(
                    f"Invalid {element} type '{type}' \n"
                    f"Valid types: {list(self._element_types[element].keys())}"
                )
        else:
            raise ValueError(
                f"Invalid element type '{element}' \n"
                f"Valid element types: {list(self._element_types.keys())}"
            )


class VideoAnalyzer(VideoAnalysis):
    """Main video handling class
            * Load frames from video files
            * Load mask files
            * Load/save measurement metadata
    """
    video: VideoFileHandler
    design: DesignFileHandler
    transform: Transform

    _element_types: dict = {
        'video': {
            'opencv': VideoFileHandler,
        },
        'design': {
            'svg': DesignFileHandler,
        },
        'transform': {
            'perspective': PerspectiveTransform,
        },
    }

    dt: float
    Nf: int
    video_type: str
    design_type: str
    transform_type: str

    __default__ = {
        'dt': 5,
        # time interval in seconds  # todo: switch between dt/Nf options?
        'Nf': 100,  # number of frames to analyze
        'video_type': 'opencv',
        'design_type': 'svg',
        'transform_type': 'perspective',
    }

    def __init__(self, video_path, design_path, config: dict = None):
        super(VideoAnalyzer, self).__init__(config)

        video = self.get_element('video', self.video_type)
        design = self.get_element('design', self.design_type)
        transform = self.get_element('transform', self.transform_type)

        assert isinstance(video, type(VideoFileHandler))  # todo: annoying that we have to do this... but do we?
        assert isinstance(design, type(DesignFileHandler))
        assert isinstance(transform, type(Transform))

        self.video = video(video_path, config)
        self.design = design(design_path, config)
        self.transform = transform(self.design.shape, config)


class MultiVideoAnalyzer(VideoAnalysis):
    pass


class guiTransform(guiPane):
    """A manual transform selection pane
    """
    pass


class guiFilter(guiPane):
    """A manual filter selection pane
    """
    pass


class guiProgress(guiPane):
    """A progress pane
    """
    pass