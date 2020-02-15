import sys
import abc
import re
from typing import Tuple, NamedTuple, Callable, Dict, Type, Generator, Any, Optional, List
from contextlib import contextmanager
import os

import numpy as np
import cv2

from OnionSVG import OnionSVG, check_svg

from isimple.maths.images import ckernel, to_mask, crop_mask, area_pixelsum
from isimple.plumbing import RootException, VideoAnalysisElement, CachingVideoAnalysisElement
from isimple.registry import Registry, registry, endpoint
from isimple.util import restrict
from isimple.gui import guiPane
from isimple.meta import Factory, ColorSpace, FrameIntervalSetting


class AnalysisSetupError(RootException):
    msg = 'Error in analysis setup'


class VideoFileTypeError(AnalysisSetupError):
    msg = 'Unrecognized video file type'  # todo: formatting


class AnalysisError(RootException):
    msg = 'Error during analysis'


class VideoFileHandler(CachingVideoAnalysisElement):
    """Interface to video files ~ OpenCV
    """
    colorspace: str

    __default__ = {
        'colorspace': ColorSpace('hsv'),
    }
    __registry__ = registry.VideoFileHandler

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
        self.shape = (
            int(self._capture.get(cv2.CAP_PROP_FRAME_WIDTH)),
            int(self._capture.get(cv2.CAP_PROP_FRAME_HEIGHT))
        )

        if self.frame_count == 0:
            raise VideoFileTypeError

    def _set_position(self, frame_number: int):
        self._capture.set(cv2.CAP_PROP_POS_FRAMES, frame_number)
        self._get_position()

    def _get_position(self) -> int:
        self.frame_number = self._capture.get(cv2.CAP_PROP_POS_FRAMES)
        return self.frame_number

    def _read_frame(self, path: str, frame_number: int) -> np.ndarray:
        """Read frame from video file, HSV color space
            the `path` parameter is included to determine the cache key
            in order to make this function cachable across multiple files.
        """
        self._set_position(frame_number)
        ret, frame = self._capture.read()

        if ret:
            # Convert to colorspace
            if self.colorspace == ColorSpace('hsv'):
                frame = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV, frame)
            return frame

    @registry.VideoFileHandler.expose(endpoint.get_raw_frame)
    def read_frame(self, frame_number: int) -> Optional[np.ndarray]:
        return self._cached_call(self._read_frame, self.path, frame_number)


class VideoHandlerType(Factory):
    _mapping = {
        'opencv':   VideoFileHandler,
    }


class Transform(VideoAnalysisElement):
    """Handles coordinate transforms.
    """
    _shape: tuple
    _transform: Optional[np.ndarray]

    transform_matrix: np.ndarray

    __default__ = {
        'transform_matrix': None
    }

    def __init__(self, shape, config):
        super(Transform, self).__init__(config)
        self._shape = shape[0:2]  # Don't include color dimension

        self._transform = None
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
    __registry__ = registry.IdentityTransform

    def set(self, transform: np.ndarray):
        pass

    @registry.IdentityTransform.expose(endpoint.estimate_transform)
    def estimate(self, coordinates):
        pass

    def __call__(self, img: np.ndarray) -> np.ndarray:
        return img


class PerspectiveTransform(Transform):
    __registry__ = registry.PerspectiveTransform

    def set(self, transform: np.ndarray):
        self._transform = transform

    @registry.PerspectiveTransform.expose(endpoint.estimate_transform)
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
            frame, self._transform, self._shape, dst=frame
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
    __registry__ = registry.HsvRangeFilter

    def __init__(self, config: dict):
        super(HsvRangeFilter, self).__init__(config)

    def mean_color(self) -> np.ndarray:
        # todo: S and V are arbitrary for now
        return np.array([np.mean([self.c0[0], self.c1[0]]), 255, 200])

    @registry.HsvRangeFilter.expose(endpoint.set_filter_from_color)
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
    filter_type: Filter

    __default__ = {
        'render_dir': os.path.join(os.getcwd(), '.render'),
        'filter_type': FilterType(),    # class of filter
    }

    def __init__(self, mask: np.ndarray, name: str, config: dict = None, filter: Filter = None):
        super(Mask, self).__init__(config)
        self._full = mask
        self.name = name

        self._full = mask
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


class DesignFileHandler(CachingVideoAnalysisElement):
    _overlay: np.ndarray
    _masks: List[Mask]  # Number of masks shouldn't be changed after initialization

    dpi: int
    render_dir: str
    keep_renders: bool
    overlay_alpha: float
    kernel: np.ndarray

    __default__ = {
        'dpi': 400,  # DPI to render .svg at
        'render_dir': os.path.join(os.getcwd(), '.render'),
        'keep_renders': False,
        'overlay_alpha': 0.1,
        'kernel': ckernel(7),       # mask smoothing kernel
    }

    def __init__(self, path: str, config: dict = None):
        super(DesignFileHandler, self).__init__(config)

        if not os.path.isfile(path):
            raise FileNotFoundError

        self._path = path
        with self.caching():
            self._overlay = self.peel_design(path)

            self._masks = [
                Mask(mask, name, config) for mask, name in zip(*self.read_masks(path))
            ]


            if not self.keep_renders:
                self._clear_renders()

        self._shape = self._overlay.shape  # todo: all Transform objects need to know about this

    def _clear_renders(self):
        renders = [f for f in os.listdir(self.render_dir)]
        for f in renders:
            os.remove(os.path.join(self.render_dir, f))

    def _peel_design(self, design_path) -> np.ndarray:

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

        return overlay

    def _read_masks(self, _) -> Tuple[List[np.ndarray], List[str]]:
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
        names = []
        for path in sorted_files:
            masks.append(to_mask(cv2.imread(path), self.kernel))

            match = pattern.search(path)
            if match:
                names.append(match.groups()[1].strip())
            else:
                names.append(path)

        if not self.keep_renders:
            self._clear_renders()

        return masks, names

    def peel_design(self, design_path) -> np.ndarray:
        return self._cached_call(self._peel_design, design_path)

    def read_masks(self, design_path) -> Tuple[List[np.ndarray], List[str]]:
        return self._cached_call(self._read_masks, design_path)

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

    _elements: Tuple[VideoAnalysisElement, ...]

    def __init__(self, elements: Tuple[VideoAnalysisElement, ...]):
        self._elements = elements

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
    _features: Tuple[Feature, ...]
    _colors: Tuple[np.ndarray, ...]

    def __init__(self, features: Tuple[Feature, ...]):
        self._features = features
        self._colors = self.get_colors()

    def get_colors(self) -> Tuple[np.ndarray, ...]:
        if not hasattr(self, '_colors'):
            # Get guideline colors for all features
            colors = tuple([f._guideline_color() for f in self._features])

            # todo: dodge colors

            # Set the _color for all features
            for feature, color in zip(self._features, colors):
                feature._color = color

            self._colors = colors
        else:
            colors = self._colors

        return colors


def frame_to_none(frame: np.ndarray) -> None:    # todo: this is dumb
    return None


class SimpleFeature(Feature):  # todo: Simple and SIMPLE are a bad fit (:
    _function = staticmethod(frame_to_none)  # Override in child classes

    mask: Mask
    filter: Filter

    def __init__(self, mask: Mask, filter: Filter = None):
        if filter is None:
            assert isinstance(mask.filter, Filter), AnalysisSetupError
            filter = mask.filter

        self.mask = mask
        self.filter = filter

        super(SimpleFeature, self).__init__((mask, filter))

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


class VideoAnalysis(VideoAnalysisElement):
    _elements: List[VideoAnalysisElement]
    _element_types: dict = {
        'element': {
            'type': VideoAnalysisElement
        }
    }

    _callbacks: AnalysisCallbacks
    __registry__: Registry
    __instance__: Dict[str, VideoAnalysisElement]  # todo: ugh naming

    def __init__(self, config):
        super(VideoAnalysis, self).__init__(config)
        self.__instance__ = {k: self for k in self.__registry__.signatures()}
        self._elements = []

    def _add_element(self, element_type: Type[VideoAnalysisElement], *args, **kwargs) -> VideoAnalysisElement:
        """Add VideoAnalysisElement instances to VideoAnalyzer
        """
        signatures = self.signatures() + element_type.signatures()

        if len(signatures) == len(set(signatures)):   # todo: add sanity check here
            element = element_type(*args, **kwargs)  # todo: add checks ~ whether all of this makes sense etc
            self._elements.append(element)
            self.__instance__.update(
                {k:element for k in element.signatures()}
            )
            return element
        else:
            raise AnalysisSetupError("something something collision and explain it")

    def set_callbacks(self, callbacks: AnalysisCallbacks):
        self._callbacks = callbacks

    def _calculate_callback(self, value: List[Any], state: List[np.ndarray]):
        """Perform analysis for a given frame number
        """
        assert len(value) == len(state), AnalysisSetupError

        if value is not None:
            for callback in self._callbacks.value:
                callback(value)
        if state is not None:
            for callback in self._callbacks.value:
                callback(state)

    @contextmanager
    def caching(self):
        """Caching contest on VideoAnalysis: propagate context to elements
            that implement caching
        """
        caching_elements = [
            e for e in self._elements if isinstance(e, CachingVideoAnalysisElement)
        ]
        try:
            for element in caching_elements:
                element.__enter__()
            yield self
        finally:
            for element in caching_elements:
                element.__exit__(*sys.exc_info())

    def signatures(self):
        return list(self.__instance__.keys())

    def exposes(self, signature):
        """Check if own class or class of any contained VideoAnalysisElement 
            instances exposes method specified with signature
        """  # todo: what about collisions?

        return signature in self.__instance__

    def call(self, signature, *args, **kwargs):
        """Call the method specified in signature 
        """  # todo: check exposes here, or trust the implementation?
        if self.exposes(signature):
            return self.__instance__[signature].call(*args, **kwargs)
        else:
            raise NotImplementedError(f"{self.__class__.__name__} does not "
                                      f"expose {signature}")

    def get_callback(self, signature):
        if self.exposes(signature):
            method_name = self.__instance__[signature]._mapping[signature].__name__
            return getattr(self.__instance__[signature], method_name)
        else:
            raise NotImplementedError(f"{self.__class__.__name__} does not "
                                      f"expose {signature}")


class VideoAnalyzer(VideoAnalysis):
    """Main video handling class
            * Load frames from video files
            * Load mask files
            * Load/save measurement metadata
    """
    video: VideoFileHandler
    design: DesignFileHandler
    transform: Transform

    featuresets: List[FeatureSet]

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
    video_type: Type[VideoFileHandler]
    design_type: Type[DesignFileHandler]
    transform_type: Type[Transform]

    __default__ = {
        'frame_interval_setting':   FrameIntervalSetting(),
        'dt':                       5.0,
        'Nf':                       100,
        'video_type':               VideoHandlerType(),
        'design_type':              DesignHandlerType(),
        'transform_type':           TransformType(),
    }
    __registry__ = registry.VideoAnalyzer

    def __init__(self, video_path: str, design_path: str,
                 feature_types: List[Type[Feature]], config: dict = None):
        super(VideoAnalyzer, self).__init__(config)

        self.video = self._add_element(self.video_type, video_path, config) # type: ignore  # todo: fix typing
        self.design = self._add_element(self.design_type, design_path, config) # type: ignore
        self.transform = self._add_element(self.transform_type, self.video.shape, config) # type: ignore

        self.featuresets = [
            FeatureSet(
                    tuple(feature_type(mask) for mask in self.design.masks)
                ) for feature_type in feature_types
        ]

    def frame_numbers(self) -> Generator[int, None, None]:
        frame_count = self.video.frame_count
        fps = self.video.fps

        if self.frame_interval_setting == FrameIntervalSetting('Nf'):
            Nf = min(self.Nf, frame_count)
            for f in np.linspace(0, frame_count, Nf):
                yield int(f)
        elif self.frame_interval_setting == FrameIntervalSetting('dt'):
            df = restrict(self.dt * fps, 1, frame_count)
            for f in np.arange(0, frame_count, df):
                yield int(f)
        else:
            raise ValueError(f"Unexpected frame interval setting "
                             f"{self.frame_interval_setting}")

    @registry.VideoAnalyzer.expose(endpoint.get_transformed_frame)
    def get_transformed_frame(self, frame_number: int) -> np.ndarray:  # todo: also called from gui
        return self.transform(self.video.read_frame(frame_number))# todo: depending on self.frame is dangerous in case we want to run this in a different thread

    @registry.VideoAnalyzer.expose(endpoint.get_transformed_overlaid_frame)
    def get_frame_overlay(self, frame_number: int) -> np.ndarray:  # todo: also called from gui
        return self.design.overlay(self.get_transformed_frame(frame_number))

    def calculate(self, frame_number: int):
        """Return a state image for each FeatureSet
        """
        frame = self.get_transformed_frame(frame_number)

        V = []
        S = []
        for fs in self.featuresets:
            values = []
            state = np.zeros(frame.shape, dtype=np.uint8) # todo: can't just set it to self.frame.dtype?
            # todo: may be faster / more memory-efficient to keep state[i] and set it to 0

            for feature in fs._features:  # todo: make featureset iterable maybe
                value, state = feature.calculate(
                    frame.copy(),  # don't overwrite self.frame ~ cv2 dst parameter  # todo: better to let OpenCV handle copying, or not?
                    state               # additive; each feature adds to state
                )
                values.append(value)

            # Add overlay on top of state
            state = self.design.overlay(state)

            V.append(values)   # todo value values value ugh
            S.append(state)

        self._calculate_callback(V,S)

    def analyze(self):
        for fn in self.frame_numbers():
            self.calculate(fn)


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