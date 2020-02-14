from diskcache import Cache
import cv2
import os
import re
import time
import logging
from typing import Tuple, List, Optional, Any, Type, NamedTuple, Callable, Generator
import numpy as np
from OnionSVG import OnionSVG, check_svg
import abc
import threading
from collections import namedtuple

from isimple.maths.images import ckernel, to_mask, crop_mask, area_pixelsum
from isimple.util import describe_function
from isimple.gui import guiPane
from isimple.meta import *


class AnalysisSetupError(Exception):
    pass


class VideoFileTypeError(AnalysisSetupError):
    pass


class AnalysisError(Exception):
    pass


class VideoAnalysisElement(abc.ABC):  # todo: more descriptive name
    __default__: dict
    __default__ = {  # EnforcedStr instances should be instantiated without
    }                #  arguments, otherwise there may be two defaults!

    # todo: interface with isimple.meta
    # todo: define legal values for strings so config can be validated at this level

    def __init__(self, config):
        self._config = self.handle_config(config)

    def handle_config(self, config: dict = None) -> dict:
        """Handle a (flat) configuration dict
            - Look through __default__ dict of all classes in __bases__
            - For all of the keys defined in __default__:
                -> if key not in config, use the default key
                -> if default value is an EnforcedStr and key is present in
                    config, validate the value
                -> if default value is a Factory and key is present in
                    config, validate and resolve to the associated class
            - Keys in config that are not defined in __default__ are skipped
        :param config:
        :return:
        """
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
                if isinstance(default, EnforcedStr):
                    # Pass config[key] through EnforcedStr
                    _config[key] = default.__class__(config[key])
                else:
                    _config[key] = config[key]
            else:
                _config[key] = default

            # Catch Factory instances, even if it's the default
            if isinstance(_config[key], Factory):
                # Get mapped class
                _config[key] = _config[key].get()  # type: ignore

        return _config

    def __getattr__(self, item):  # todo: relatively annoying as this can't be linted...
        """Get attribute value from self._config  
        """  # todo: interface with metadata -> should raise an exception if unexpected attribute is got
        return self._config[item]

    def __len__(self):
        pass # todo: this is a workaround, PyCharm debugger keeps polling __len__ for some reason


    def __call__(self, frame: np.ndarray) -> np.ndarray:
        raise NotImplementedError


class VideoFileHandler(VideoAnalysisElement):
    """Interface to video files ~ OpenCV
    """
    _cache: Optional[Cache]
    _background: Optional[threading.Thread]

    do_cache: bool
    do_background: bool
    cache_dir: str
    cache_size_limit: int
    colorspace: str

    __default__ = {
        'do_cache': False,
        'do_background': False, # True -> start background caching thread along with cache
        'cache_dir': os.path.join(os.getcwd(), '.cache'),
        'cache_size_limit': 2 ** 32,                        # cache size limit
        'colorspace': ColorSpace('hsv'),
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

        self.frame_count = int(self._capture.get(cv2.CAP_PROP_FRAME_COUNT))
        self.fps = self._capture.get(cv2.CAP_PROP_FPS)
        self.frame_number = int(self._capture.get(cv2.CAP_PROP_POS_FRAMES))

        if self.frame_count == 0:
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

    def read_frame(self, frame_number: int = None, from_cache = False):
        """Read frame from video file, HSV color space
        """
        if frame_number is None:
            frame_number = self.frame_number

        key = self._get_key(self.read_frame, frame_number)
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
                    frame_number = int(self.frame_count / 2)

                self._set_position(frame_number)
                ret, frame = self._capture.read()

                # Convert to colorspace
                if self.colorspace == ColorSpace('hsv'):
                    frame = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV, frame)

                if ret:
                    self._cache.set(key, frame)
                    return frame

    def __enter__(self):
        self._cache = Cache(
            directory=self.cache_dir,
            size_limit=self.cache_size_limit,
        )
        if self.do_background:
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


class VideoHandlerType(Factory):
    _mapping = {
        'opencv':   VideoFileHandler,
    }


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


class TransformType(Factory):
    _mapping = {
        'perspective':  PerspectiveTransform,
        'identity':     IdentityTransform,
    }


class Filter(VideoAnalysisElement):
    """Handles pixel filtering operations
    """
    def __init__(self, config: dict = None):
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
        return np.array([np.mean([self.c0[0], self.c1[0]]), 255, 200])

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


class FilterType(Factory):
    _mapping = {
        'hsv range':    HsvRangeFilter,
    }


class Mask(VideoAnalysisElement):
    """Handles masks in the context of a video file
    """

    filter: Filter

    render_dir: str
    kernel: np.ndarray
    filter_type: Filter

    __default__ = {
        'render_dir': os.path.join(os.getcwd(), '.render'),
        'kernel': ckernel(7),           # mask smoothing kernel
        'filter_type': FilterType(),    # class of filter
    }

    def __init__(self, path: str, config: dict = None, filter: Filter = None):
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

        if filter is None:
            filter = self.filter_type(config)
            assert isinstance(filter, Filter), AnalysisSetupError
        self.filter = filter

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
    overlay_alpha: float

    __default__ = {
        'dpi': 400,  # DPI to render .svg at
        'render_dir': os.path.join(os.getcwd(), '.render'),
        'keep_renders': False,
        'overlay_alpha': 0.1,
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

    def overlay(self, frame: np.ndarray) -> np.ndarray:
        cv2.addWeighted(
            self._overlay, self.overlay_alpha,
            frame, 1 - self.overlay_alpha,
            gamma=0, dst=frame
        )  # todo: could cause issues since frame is HSV by default
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB, dst=frame)
        return frame

    @property
    def masks(self):
        return self._masks


class DesignHandlerType(Factory):
    _mapping = {
        'svg':      DesignFileHandler,
    }


class Feature(abc.ABC):
    _color: Optional[np.ndarray]
    _state: Optional[np.ndarray]

    def __init__(self, _: Mask, *args, **kwargs):
        pass

    def calculate(self, frame: np.ndarray, state: np.ndarray = None) \
            -> Tuple[Any, np.ndarray]:
        """Calculate Feature for given frame
            and update state image (optional)
        """
        if state is not None:
            state = self.state(frame, state)
        return self.value(frame), state

    @property
    def color(self) -> np.ndarray:
        """Color of the Feature in figures.

            A Feature's color must be set as not to overlap with
            other Features in the same FeatureSet.
            Therefore, <Feature>._color must be determined by FeatureSet!
        """
        return self._color

    @abc.abstractmethod
    def _guideline_color(self) -> np.ndarray:
        """Returns the 'guideline color' of a Feature instance
            Used by FeatureSet to determine the actual _color
        """
        raise NotImplementedError

    @abc.abstractmethod
    def state(self, frame: np.ndarray, state: np.ndarray = None) -> np.ndarray:
        """Return the Feature instance's state image for a given frame
        """
        raise NotImplementedError

    @abc.abstractmethod
    def value(self, frame: np.ndarray) -> Any:
        """Compute the value of the Feature instance for a given frame
        """
        raise NotImplementedError


class FeatureSet(object):
    _features: List[Feature]
    _colors: List[np.ndarray]

    def __init__(self, features: List[Feature]):
        self._features = features
        self._colors = self.get_colors()

    def get_colors(self) -> List[np.ndarray]:
        if not hasattr(self, '_colors'):
            # Get guideline colors for all features
            colors = [f._guideline_color() for f in self._features]

            # todo: dodge colors

            # Set the _color for all features
            for feature, color in zip(self._features, colors):
                feature._color = color
        else:
            colors = self._colors

        return colors


def frame_to_none(frame: np.ndarray) -> None:
    return None


class SimpleFeature(Feature):  # todo: Simple and SIMPLE are a bad fit (:
    _function = staticmethod(frame_to_none)  # Override in child classes

    mask: Mask
    filter: Filter

    def __init__(self, mask: Mask, filter: Filter = None):
        super(SimpleFeature, self).__init__(mask, filter)
        if filter is None:
            assert isinstance(mask.filter, Filter), AnalysisSetupError
            filter = mask.filter

        self.mask = mask
        self.filter = filter

    def _guideline_color(self) -> np.ndarray:
        return self.filter.mean_color()

    def value(self, frame) -> Any:
        return self._function(self.filter(self.mask(frame)))

    def state(self, frame: np.ndarray, state: np.ndarray = None) -> np.ndarray:
        if state is not None:
            return state


class Area(SimpleFeature):
    _function = staticmethod(area_pixelsum)


class AnalysisCallbacks(NamedTuple):
    setup: List[Callable]  # todo: some standardized way to communicate configuration (colors, amount of plots, ranges, sizes)
    value: List[Callable[[Any], None]]
    state: List[Callable[[np.ndarray], None]]


class VideoAnalysis(abc.ABC):
    value: Optional[List[Any]]
    state: Optional[List[np.ndarray]]


    _elements: List[VideoAnalysisElement]
    _element_types: dict = {
        'element': {
            'type': VideoAnalysisElement
        }
    }

    _callbacks: AnalysisCallbacks

    def _add_elements(self, elements: List[VideoAnalysisElement]):
        """Add VideoAnalysisElement instances to VideoAnalyzer
        """
        for e in elements:
            if True:   # todo: add sanity check here
                self._elements.append(e)

    def set_callbacks(self, callbacks: AnalysisCallbacks):
        self._callbacks = callbacks

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

    def calculate(self, frame_number: int = None):
        """Perform analysis for a given frame number
        """
        if self.__class__.__name__ == 'VideoAnalysis':  # todo cleaner way to check for this?
            raise NotImplementedError

        if self.value is not None:
            for callback in self._callbacks.value:
                callback(self.value)
        if self.value is not None:
            for callback in self._callbacks.value:
                callback(self.state)


class VideoAnalyzer(VideoAnalysisElement, VideoAnalysis):
    """Main video handling class
            * Load frames from video files
            * Load mask files
            * Load/save measurement metadata
    """
    video: VideoFileHandler
    design: DesignFileHandler
    transform: Transform

    featuresets: List[FeatureSet]

    frame: Optional[np.ndarray]
    value: List[List[Any]]
    state: List[np.ndarray]

    frame_number: int

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

    frame_interval_setting: FrameIntervalSetting  # use dt or Nf
    dt: float                                     # interval in seconds
    Nf: int                                       # number of evenly spaced frames
    video_type: VideoFileHandler
    design_type: DesignFileHandler
    transform_type: Transform

    __default__ = {
        'frame_interval_setting':   FrameIntervalSetting(),
        'dt':                       5,
        'Nf':                       100.0,
        'video_type':               VideoHandlerType(),
        'design_type':              DesignHandlerType(),
        'transform_type':           TransformType(),
    }

    def __init__(self, video_path: str, design_path: str,
                 feature_types: List[Type[Feature]], config: dict = None):
        super(VideoAnalyzer, self).__init__(config)

        assert isinstance(self.video_type, type(VideoFileHandler))  # todo: annoying that this is necessary for MyPy / inspections
        assert isinstance(self.design_type, type(DesignFileHandler))
        assert isinstance(self.transform_type, type(Transform))

        self.video = self.video_type(video_path, config)
        self.design = self.design_type(design_path, config)
        self.transform = self.transform_type(self.design.shape, config)

        self.featuresets = [
            FeatureSet(
                    [feature_type(mask) for mask in self.design.masks]
                ) for feature_type in feature_types
        ]

    def get_next_frame_number(self) -> Generator[int, None, None]:
        """
        """
        frame_count = self.video.frame_count
        fps = self.video.fps

        if self.frame_interval_setting == FrameIntervalSetting('Nf'):
            for f in np.linspace(0, frame_count, self.Nf):
                yield int(f)
        elif self.frame_interval_setting == FrameIntervalSetting('dt'):
            for f in np.arange(0, frame_count, self.dt / fps):
                yield int(f)
        else:
            raise ValueError(f"Unexpected frame interval setting "
                             f"{self.frame_interval_setting}")

    def get_frame(self, frame_number: int = None) -> np.ndarray:
        if frame_number is None:   # todo: depending on self.frame is dangerous in case we want to run this in a different thread
            frame_number = self.frame_number
        else:
            self.frame_number = frame_number

        self.frame = self.transform(self.video.read_frame(frame_number))
        return self.frame

    def get_frame_overlay(self, frame_number: int = None) -> np.ndarray:
        if self.frame is None:   # todo: depending on self.frame is dangerous in case we want to run this in a different thread
            self.frame = self.get_frame(frame_number)
        # don't overwrite self.frame with the overlaid frame!
        return self.design.overlay(self.frame.copy())

    def calculate(self, frame_number: int = None):
        """Return a state image for each FeatureSet
        """
        if self.frame is None:  # todo: depending on self.frame is dangerous in case we want to run this in a different thread
            self.frame = self.get_frame(frame_number)

        self.value = []
        self.state = []
        for fs in self.featuresets:
            values = []
            state = np.zeros(self.frame.shape, dtype=np.uint8) # todo: can't just set it to self.frame.dtype?
            # todo: may be faster / more memory-efficient to keep state[i] and set it to 0

            for feature in fs._features:  # todo: make featureset iterable maybe
                value, state = feature.calculate(
                    self.frame.copy(),  # don't overwrite self.frame ~ cv2 dst parameter  # todo: better to let OpenCV handle copying, or not?
                    state               # additive; each feature adds to state
                )
                values.append(value)

            # Add overlay on top of state
            state = self.design.overlay(state)

            self.value.append(values)   # todo value values value ugh
            self.state.append(state)

        super(VideoAnalyzer, self).calculate()

    def __enter__(self):
        """Wrap VideoFileHandler context
        """
        self.video.__enter__()

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Wrap VideoFileHandler context
        """
        self.video.__exit__(exc_type, exc_val, exc_tb)


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