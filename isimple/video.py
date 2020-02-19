import abc
import re
from typing import Tuple, Any, Optional, List, Type, Generator, Union, Callable
import os

import numpy as np
import cv2

import copy

from OnionSVG import OnionSVG, check_svg

from isimple.core.util import *
from isimple.core.common import Manager
from isimple.core.backend import BackendInstance, CachingBackendInstance, BackendManager, BackendSetupError
from isimple.core.features import Feature, FeatureSet
from isimple.core.meta import Factory, ColorSpace, FrameIntervalSetting

from isimple.maths.images import ckernel, to_mask, crop_mask, area_pixelsum

from isimple.endpoints import BackendEndpoints
from isimple.endpoints import GuiEndpoints as gui


backend = BackendEndpoints()


class VideoFileTypeError(BackendSetupError):
    msg = 'Unrecognized video file type'  # todo: formatting


class VideoFileHandler(CachingBackendInstance):
    """Interface to video files ~ OpenCV
    """
    colorspace: str

    __default__ = {
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

    def _set_position(self, frame_number: int):  # todo: add a mechanism to restrict the frame_number to a limited number of options -- take the nearest 'legal' one -> fill out the cache during seeking before the actual analysis. This will make seeking slower though..
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

    @backend.expose(backend.get_total_frames)
    def get_total_frames(self) -> int:
        return self.frame_count

    @backend.expose(backend.get_raw_frame)
    def read_frame(self, frame_number: int) -> Optional[np.ndarray]:
        return self._cached_call(self._read_frame, self.path, frame_number)

    @backend.expose(backend.get_time)
    def get_time(self, frame_number: int) -> float:
        return frame_number / self.fps

    @backend.expose(backend.get_fps)
    def get_fps(self) -> float:
        return self.fps


class VideoHandlerType(Factory):
    _mapping = {
        'opencv':   VideoFileHandler,
    }


class DynamicHandler(object):
    _implementation: object
    _implementation_factory = Factory
    _implementation_class = object

    def set_implementation(self, implementation: str) -> str:
        impl_type: type = self._implementation_factory(implementation).get()
        assert issubclass(impl_type, self._implementation_class)

        self._implementation = impl_type()
        return self._implementation_factory.get_str(
            self._implementation.__class__
        )


class TransformInterface(abc.ABC):
    default = np.eye(3)

    @abc.abstractmethod
    def validate(self, transform: np.ndarray) -> bool:
        raise NotImplementedError

    @abc.abstractmethod
    def estimate(self, coordinates: list, shape: tuple) -> np.ndarray:  # todo: explain what and why shape is
        raise NotImplementedError

    @abc.abstractmethod
    def transform(self, img: np.ndarray, transform: np.ndarray, shape: tuple) -> np.ndarray:
        raise NotImplementedError

    @abc.abstractmethod
    def inverse_transform(self, img: np.ndarray, transform: np.ndarray, shape: tuple):
        raise NotImplementedError


class IdentityTransform(TransformInterface):
    """Looks like a Transform, but doesn't transform
    """
    def validate(self, transform):
        return True

    def estimate(self, coordinates: list, shape: tuple) -> np.ndarray:
        return np.eye(3)

    def transform(self, img: np.ndarray, transform: np.ndarray, shape: tuple) -> np.ndarray:
        return img

    def inverse_transform(self, img: np.ndarray, transform: np.ndarray, shape: tuple):
        return img


class PerspectiveTransform(TransformInterface):
    def validate(self, transform: np.ndarray) -> bool:
        return transform.shape == (3, 3)

    def estimate(self, coordinates: list, shape: tuple) -> dict:
        return cv2.getPerspectiveTransform(
            np.float32(coordinates),
            np.float32(
                np.array(  # selection rectangle: bottom left to top right
                    [
                        [0, shape[1]],
                        [0, 0],
                        [shape[0], 0],
                        [shape[0], shape[1]],
                    ]
                )
            )
        )

    def transform(self, img: np.ndarray, transform: np.ndarray, shape: tuple) -> np.ndarray:
        return cv2.warpPerspective(
            img, transform, shape,# dst=img  # todo: can't use destination image here! it's the wrong shape!
        )

    def inverse_transform(self, img: np.ndarray, transform: np.ndarray, shape: tuple):
        raise NotImplementedError


class TransformType(Factory):
    _mapping = {
        'perspective': PerspectiveTransform,
        'identity': IdentityTransform,
    }


class TransformHandler(BackendInstance, DynamicHandler):
    """Handles coordinate transforms.
    """
    _shape: tuple
    _transform: Optional[np.ndarray]

    _implementation: TransformInterface
    _implementation_factory = TransformType
    _implementation_class = TransformInterface

    transform_matrix: np.ndarray

    __default__ = {
        'transform_matrix': None,
        'transform_type': str(TransformType()),
    }

    def __init__(self, shape, config):
        super(TransformHandler, self).__init__(config)
        self.set_implementation(self.transform_type)
        self._shape = shape[0:2]  # Don't include color dimension

        self._transform = None
        if self.transform_matrix is not None:
            self.set(self.transform_matrix)
        else:
            self.set(self._implementation.default)

    @backend.expose(backend.set_transform_implementation)
    def set_implementation(self, implementation: str) -> str:
        return super(TransformHandler, self).set_implementation(implementation)

    def set(self, transform: np.ndarray):
        """Set the transform matrix
        """
        if self._implementation.validate(transform):
            self._transform = transform
        else:
            raise ValueError(f"Invalid transform {transform} for "
                             f"'{self._implementation.__class__.__name__}'")

    @backend.expose(backend.estimate_transform)
    def estimate(self, coordinates: list) -> None:
        """Estimate the transform matrix from a set of coordinates.
            Coordinates should correspond to the corners of the outline of
            the design, ordered from the bottom left to the top right.
        """
        self.set(self._implementation.estimate(coordinates, self._shape))

    @backend.expose(backend.transform)
    def __call__(self, img: np.ndarray) -> np.ndarray:
        """Transform a frame.
            Writes to the provided variable!
            If caller needs the original value, they should copy explicitly
        """
        return self._implementation.transform(img, self._transform, self._shape)

    def inverse(self, img: np.ndarray) -> np.ndarray:
        raise NotImplementedError


class FilterInterface(abc.ABC):
    """Handles pixel filtering operations
    """
    default: dict = {}

    @abc.abstractmethod
    def set_filter(self, filter: dict) -> dict:
        raise NotImplementedError

    @abc.abstractmethod
    def mean_color(self, filter: dict) -> list:  # todo: add custom np.ndarray type 'hsvcolor'
        raise NotImplementedError

    @abc.abstractmethod
    def filter(self, image: np.ndarray, filter: dict) -> np.ndarray:  # todo: add custom np.ndarray type 'image'
        raise NotImplementedError


class HsvRangeFilter(FilterInterface):  # todo: may be better to **wrap** this in Filter instead of inheriting from it
    """Filters by a range of hues ~ HSV representation
    """
    default = {  # todo: may be better to make it an implementation-specific namedtuple; use that for validation/normalization also
            'hue_radius': 10,               # Radius to determine range from one color
            'sat_window': [50, 255],
            'val_window': [50, 255],
            'c0': [90, 50, 50],             # Start of filtering range (in HSV space)
            'c1': [110, 255, 255],          # End of filtering range (in HSV space)
        }

    def validate(self, filter):  # todo: may be better to 'normalize' the filter dict -- i.e. replace all fields that weren't found with the defaults
        return all(attr in self.default for attr in filter)

    def set_filter(self, filter: dict) -> dict:
        filter['hue'] = filter['color'][0]

        filter['c0'] = np.array([
            filter['hue'] - filter['hue_radius'], filter['sat_window'][0], filter['val_window'][0]
        ])
        filter['c1'] = np.array([
            filter['hue'] + filter['hue_radius'], filter['sat_window'][1], filter['val_window'][1]
        ])  # todo: plot color was set from here originally, but Filter shouldn't care about that

        return filter

    def mean_color(self, filter) -> list:
        # todo: S and V are arbitrary for now
        return list([np.mean([filter['c0'][0], filter['c1'][0]]), 255, 200])

    def filter(self, img: np.ndarray, filter) -> np.ndarray:
        return cv2.inRange(img, np.float32(filter['c0']), np.float32(filter['c1']), img)


class FilterType(Factory):
    _mapping = {
        'hsv range':    HsvRangeFilter,
    }


class FilterHandler(BackendInstance, DynamicHandler):
    _implementation: FilterInterface
    _implementation_factory = FilterType
    _implementation_class = FilterInterface

    __default__ = {
        'filter_type': str(FilterType()),
        'filter': FilterType().get().default,  #type: ignore
        'color': list,
    }

    def __init__(self, config: dict = None):
        super(FilterHandler, self).__init__(config)
        self.set_implementation(self.filter_type)

    @backend.expose(backend.get_filter_mean_color)
    def mean_color(self) -> list:
        return self._implementation.mean_color(self.filter)

    @backend.expose(backend.set_filter_parameters)
    def set_filter(self, filter: dict) -> dict:
        self._config['filter'] = self._implementation.set_filter(filter)
        return self.filter

    @backend.expose(backend.get_filter_parameters)
    def get_filter(self) -> dict:
        return self._config['filter']

    @backend.expose(backend.set_filter_implementation)
    def set_implementation(self, implementation: str) -> str:
        return super(FilterHandler, self).set_implementation(implementation)

    @backend.expose(backend.filter)
    def __call__(self, frame: np.ndarray) -> np.ndarray:
        return self._implementation.filter(frame, self.filter)



class Mask(BackendInstance):
    """Handles masks in the context of a video file
    """

    filter: FilterHandler

    render_dir: str

    __default__ = {
        'h': 153e-6, # height of mask  todo: should probably be set in a different way though...
        'render_dir': os.path.join(os.getcwd(), '.render'),
        'filter_type': str(FilterType()),    # class of filter
    }

    def __init__(self, mask: np.ndarray, name: str, config: dict = None, filter: FilterHandler = None):
        super(Mask, self).__init__(config)
        self._full = mask
        self.name = name

        self._full = mask
        self._part, self._rect, self._center = crop_mask(self._full)

        # Each Mask should have its own FilterHandler instance, unless otherwise specified
        if filter is None:
            filter = FilterHandler(config)
            assert isinstance(filter, FilterHandler), BackendSetupError
        self.filter = filter

    @backend.expose(backend.mask)
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


class DesignFileHandler(CachingBackendInstance):
    _overlay: np.ndarray
    _masks: List[Mask]

    dpi: int
    render_dir: str
    keep_renders: bool
    overlay_alpha: float
    kernel: np.ndarray

    __default__ = {
        'dpi': 400,  # DPI to render .svg at  # todo: actual precision is a function of DPI ~ Transform ~ video resolution
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
        with self.caching():  # todo: maybe also do this in a separate thread? It's quite slow.
            self._overlay = self.peel_design(path)
            self._shape = (self._overlay.shape[1], self._overlay.shape[0])

            self._masks = [
                Mask(mask, name, config) for mask, name in zip(*self.read_masks(path))
            ]

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
            'all', to=self.render_dir  # todo: should maybe prepend file name to avoid overwriting previous renders?
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

    @backend.expose(backend.get_dpi)
    def get_dpi(self) -> float:
        return self.dpi

    @backend.expose(backend.get_overlay)
    def overlay(self) -> np.ndarray:
        return self._overlay

    @backend.expose(backend.overlay_frame)
    def overlay_frame(self, frame: np.ndarray) -> np.ndarray:
        frame = cv2.cvtColor(frame, cv2.COLOR_HSV2BGR)
        frame = cv2.addWeighted(
            self._overlay, self.overlay_alpha,  # https://stackoverflow.com/questions/54249728/
            frame, 1 - self.overlay_alpha,
            gamma=0, dst=frame
        )
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        return frame

    @property
    def masks(self):
        return self._masks

    @backend.expose(backend.get_mask_names)
    def get_mask_names(self) -> tuple:
        return tuple(mask.name for mask in self._masks)


class DesignHandlerType(Factory):
    _mapping = {
        'svg':      DesignFileHandler,
    }


def frame_to_none(frame: np.ndarray) -> None:    # todo: this is dumb
    return None


class MaskFilterFunction(Feature):
    _function = staticmethod(frame_to_none)  # Override in child classes

    mask: Mask
    filter: FilterHandler

    def __init__(self, mask: Mask, filter: FilterHandler = None):
        if filter is None:
            assert isinstance(mask.filter, FilterHandler), BackendSetupError
            filter = mask.filter

        self.mask = mask
        self.filter = filter

        super(MaskFilterFunction, self).__init__((mask, filter))

    def _guideline_color(self) -> list:
        return self.filter.mean_color()

    def value(self, frame) -> Any:
        return self._function(self.filter(self.mask(frame)))

    def state(self, frame: np.ndarray, state: np.ndarray = None) -> np.ndarray:
        if state is not None:
            return state


class PixelSum(MaskFilterFunction):
    _function = staticmethod(area_pixelsum)  # todo: would be cleaner if we wouldn't need to have staticmethod here :/


class VideoFeatureType(Factory):
    _mapping = {
        'pixel_sum':    PixelSum,   # todo: actually, providing the Features as a list instead of using this factory is good in the sense that it allows feature definition at a higher level.
    }


class VideoAnalyzer(BackendManager):
    """Main video handling class
            * Load frames from video files
            * Load mask files
            * Load/save measurement metadata
    """
    _gui: Optional[Manager]
    _endpoints: BackendEndpoints = backend

    video: VideoFileHandler
    design: DesignFileHandler
    transform: TransformHandler

    _featuresets: List[FeatureSet]

    frame_interval_setting: FrameIntervalSetting  # use dt or Nf
    dt: float                                     # interval in seconds
    Nf: int                                       # number of evenly spaced frames
    video_type: Type[VideoFileHandler]
    design_type: Type[DesignFileHandler]
    transform_type: Type[TransformHandler]

    __default__ = {
        'frame_interval_setting':   FrameIntervalSetting(),
        'dt':                       5.0,
        'Nf':                       100,
        'h':                        0.153e-3,
        'features':              [VideoFeatureType('pixel_sum')],
        'video_type':               VideoHandlerType(),
        'design_type':              DesignHandlerType(),
    }

    _args: dict

    def __init__(self, video_path: str = None, design_path: str = None, config: dict = None):  # todo: add optional feature list to override self._config.features
        super(VideoAnalyzer, self).__init__(config)
        self._args = ({
            'video_path': video_path,
            'design_path': design_path,
            'config': config
        })

        self._gather_instances()

    @timing
    def launch(self) -> object:
        # todo: better sanity check -- are we already launched maybe?
        video_path = self._args['video_path']
        design_path = self._args['design_path']
        config = self._args['config']

        if video_path is not None and design_path is not None:
            self.video = self.video_type(video_path, config)
            self.design = self.design_type(design_path, config)
            self.transform = TransformHandler(self.design.shape, config)
            self.masks = self.design.masks
            self.filters = [mask.filter for mask in self.masks]

            self._gather_instances()  # todo: annoying that we have to call this one explicilty, but doing it at super.__init__ makes it less dynamic

            self._featuresets = [
                FeatureSet(
                    tuple(feature.get()(mask) for mask in self.design.masks)
                ) for feature in self.features
            ]

            return self
        else:
            raise ValueError("Either the video or the design wasn't provided")  # todo: make error message more specific

    def connect(self, gui: Manager):
        # todo: sanity checks
        self._gui = gui

    def configure(self):
        if self._gui is not None:
            self._gui.get(gui.open_setupwindow)()

    def align(self):
        if self._gui is not None:
            self._gui.get(gui.open_transformwindow)()

    def pick(self, index: int):
        if self._gui is not None:
            self._gui.get(gui.open_filterwindow)(index)

    @backend.expose(backend.get_name)
    def get_name(self) -> str:
        return self.video.name

    @backend.expose(backend.get_arguments)
    def get_config(self) -> dict:
        return self._args

    @backend.expose(backend.get_h)
    def get_h(self) -> float:
        return self.h

    @backend.expose(backend.set_config)
    def set_config(self, config: dict) -> None:
        self._configure(config)  # todo: make sure that this doesn't set the attributes that **aren't** not provided to the defaults!
        self._args['config'] = config

    @backend.expose(backend.set_video_path)
    def set_video_path(self, video_path: str) -> None:
        self._args['video_path'] = video_path

    @backend.expose(backend.set_design_path)
    def set_design_path(self, design_path: str) -> None:
        self._args['design_path'] = design_path

    def frame_numbers(self) -> Generator[int, None, None]:
        if self.frame_interval_setting == FrameIntervalSetting('Nf'):
            return frame_number_iterator(self.video.frame_count, Nf = self.Nf)
        elif self.frame_interval_setting == FrameIntervalSetting('dt'):
            return frame_number_iterator(self.video.frame_count, dt = self.dt, fps = self.video.fps)
        else:
            raise ValueError(f"Unexpected frame interval setting "
                             f"{self.frame_interval_setting}")

    @backend.expose(backend.get_frame)
    def get_transformed_frame(self, frame_number: int) -> np.ndarray:
        return self.transform(self.video.read_frame(frame_number))# todo: depending on self.frame is dangerous in case we want to run this in a different thread

    @backend.expose(backend.get_inverse_transformed_overlay)
    def get_inverse_transformed_overlay(self) -> np.ndarray:
        return self.transform.inverse(self.design.overlay())

    @backend.expose(backend.get_overlaid_frame)
    def get_frame_overlay(self, frame_number: int) -> np.ndarray:
        return self.design.overlay_frame(self.get_transformed_frame(frame_number))

    @backend.expose(backend.get_colors)  # todo: per feature in each feature set; maybe better as a dict instead of a list of tuples?
    def get_colors(self) -> List[tuple]:
        return [featureset.get_colors() for featureset in self._featuresets]

    def calculate(self, frame_number: int, update_callback: Callable):
        """Return a state image for each FeatureSet
        """
        raw_frame = self.video.read_frame(frame_number)
        frame = self.transform(raw_frame)

        V = []
        S = []
        for fs in self._featuresets:  # todo: for each feature set -- export data for a separate legend to add to the state plot
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
            state = self.design.overlay_frame(state)

            V.append(values)   # todo: value values value ugh
            S.append(state)

        update_callback(
            self.video.get_time(frame_number),
            V, # todo: this is per feature in each feature set; maybe better as dict instead of list of lists?
            S,
            frame
        )

    def analyze(self):
        if self._gui is not None:
            update_callback = self._gui.get(gui.update_progresswindow)
            self._gui.get(gui.open_progresswindow)()
        else:
            def update_callback(*args, **kwargs): pass

        for fn in self.frame_numbers():
            self.calculate(fn, update_callback)

    def save(self):
        """Save video analysis results & metadata
        """
        raise NotImplementedError


class MultiVideoAnalyzer(BackendManager):
    pass