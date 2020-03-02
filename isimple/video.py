import re
import os
import pandas as pd
from typing import Any, Callable, Type, Dict
import datetime

import cv2

from OnionSVG import OnionSVG, check_svg

from isimple.core.util import *
from isimple.core.log import get_logger
from isimple.core.common import Manager
from isimple.core.backend import BackendInstance, CachingBackendInstance, DynamicHandler, BackendManager, BackendSetupError
from isimple.core.features import Feature, FeatureSet
from isimple.core.config import *
from isimple.core.config import HsvColor, __meta_ext__

from isimple.maths.images import to_mask, crop_mask, area_pixelsum, ckernel

from isimple.endpoints import BackendEndpoints
from isimple.endpoints import GuiEndpoints as gui


log = get_logger(__name__)
backend = BackendEndpoints()


class VideoFileTypeError(BackendSetupError):
    msg = 'Unrecognized video file type'  # todo: formatting


class VideoFileHandler(CachingBackendInstance):
    """Interface to video files ~ OpenCV
    """
    _requested_frames: List[int]

    colorspace: str

    _config: VideoFileHandlerConfig
    _default = VideoFileHandlerConfig()

    def __init__(self, video_path, config: VideoFileHandlerConfig = None):
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

    def set_requested_frames(self, requested_frames: List[int]) -> None:
        """Add a list of requested frames.
            Used to determine which frames to cache in the background and
            in `_resolve_frame`
        """
        log.debug(f"Requested frames: {requested_frames}")
        self._requested_frames = requested_frames

    def _resolve_frame(self, frame_number: int) -> int:
        """Resolve a frame_number to the nearest requested frame number
            This is used to limit the polled frames to the
            frames that are to be cached or are cached already.
        """
        if hasattr(self, '_requested_frames'):
            return min(
                self._requested_frames,
                key=lambda x:abs(x - frame_number)
            )
        else:
            return frame_number

    def _set_position(self, frame_number: int):
        """Set the position of the OpenCV VideoCapture.
        """
        self._capture.set(cv2.CAP_PROP_POS_FRAMES, frame_number)
        self._get_position()

    def _get_position(self) -> int:
        """Get the position of the OpenCV VideoCapture.
            Due to some internal workings of OpenCV, the actual position the
            capture object ends up at may differ from the requested position.
        """
        self.frame_number = self._capture.get(cv2.CAP_PROP_POS_FRAMES)
        return self.frame_number

    def _read_frame(self, _: str, frame_number: int) -> np.ndarray:
        """Read frame from video file, HSV color space
            the `_` parameter is a placeholder for the (unused) path of the
            video file, which is used to make the cache key in order to make
            this function cachable across multiple files.
        """
        self._set_position(frame_number)  # todo: check if it's a problem for multiple cv2.VideoCapture instances to read from the same file at the same time (case of background caching while seeking in the video)
        ret, frame = self._capture.read()

        if ret:
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV, frame)
            return frame

    @backend.expose(backend.get_total_frames)
    def get_total_frames(self) -> int:
        return self.frame_count

    @backend.expose(backend.get_time)
    def get_time(self, frame_number: int) -> float:
        return self._resolve_frame(frame_number) / self.fps

    @backend.expose(backend.get_fps)
    def get_fps(self) -> float:
        return self.fps

    @backend.expose(backend.get_raw_frame)
    def read_frame(self, frame_number: int) -> Optional[np.ndarray]:
        """Wrapper for `_read_frame`.
            Enables caching (if in a caching context!) and provides the video
            file's path to determine the cache key.
        """
        if self._config.do_resolve_frame_number:
            return self._cached_call(self._read_frame, self.path, self._resolve_frame(frame_number))
        else:
            return self._cached_call(self._read_frame, self.path, frame_number)


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


class PerspectiveTransform(TransformInterface):
    def validate(self, transform: np.ndarray) -> bool:
        return transform.shape == (3, 3)

    def estimate(self, coordinates: list, shape: tuple) -> dict:
        log.vdebug(f'Estimating transform ~ coordinates {coordinates} & shape {shape}')
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
            img, transform, shape,  # can't set destination image here! it's the wrong shape!
        )


TransformType.extend({
    'perspective': PerspectiveTransform,
})


class TransformHandler(BackendInstance, DynamicHandler):
    """Handles coordinate transforms.
    """
    _shape: tuple
    _inverse = np.ndarray

    _implementation: TransformInterface
    _implementation_factory = TransformType
    _implementation_class = TransformInterface

    transform_matrix: np.ndarray

    _config: TransformHandlerConfig
    _default = TransformHandlerConfig()

    def __init__(self, shape, config: TransformHandlerConfig):
        super(TransformHandler, self).__init__(config)
        self.set_implementation(self._config.type)
        self._shape = shape[0:2]  # Don't include color dimension

    @backend.expose(backend.set_transform_implementation)
    def set_implementation(self, implementation: str) -> str:
        # If there's ever any method to set additional transform options, this method/endpoint can be merged into that
        return super(TransformHandler, self).set_implementation(implementation)

    def set(self, transform: np.ndarray):
        """Set the transform matrix
        """
        if self._implementation.validate(transform):
            self._config.matrix = transform
            self._inverse = np.linalg.inv(transform)
        else:
            raise ValueError(f"Invalid transform {transform} for "
                             f"'{self._implementation.__class__.__name__}'")

    @backend.expose(backend.estimate_transform)
    def estimate(self, coordinates: list) -> None:
        """Estimate the transform matrix from a set of coordinates.
            Coordinates should correspond to the corners of the outline of
            the design, ordered from the bottom left to the top right.
        """
        self._config.coordinates = coordinates
        self.set(self._implementation.estimate(coordinates, self._shape))


    @backend.expose(backend.get_coordinates)
    def get_coordinates(self) -> Optional[list]:
        if isinstance(self._config.coordinates, list):
            return self._config.coordinates
        else:
            return None

    @backend.expose(backend.transform)
    def __call__(self, img: np.ndarray) -> np.ndarray:
        """Transform a frame.
            Writes to the provided variable!
            If caller needs the original value, they should copy explicitly
        """
        return self._implementation.transform(img, self.matrix, self._shape)

    def inverse(self, img: np.ndarray) -> np.ndarray:
        return self._implementation.transform(img, self._inverse, self._shape)

    @property
    def matrix(self):
        return self._config.matrix


class FilterInterface(abc.ABC):
    """Handles pixel filtering operations
    """
    _config_class: Type[FilterConfig]

    @abc.abstractmethod
    def set_filter(self, filter, color: HsvColor):
        raise NotImplementedError

    @abc.abstractmethod
    def mean_color(self, filter) -> HsvColor:  # todo: add custom np.ndarray type 'hsvcolor'
        raise NotImplementedError

    @abc.abstractmethod
    def filter(self, image: np.ndarray, filter) -> np.ndarray:  # todo: add custom np.ndarray type 'image'
        raise NotImplementedError


class HsvRangeFilter(FilterInterface):  # todo: may be better to **wrap** this in Filter instead of inheriting from it
    """Filters by a range of hues ~ HSV representation
    """
    _config_class = HsvRangeFilterConfig

    def validate(self, filter):  # todo: may be better to 'normalize' the filter dict -- i.e. replace all fields that weren't found with the defaults
        return all(attr in self._config_class() for attr in filter)

    def set_filter(self, filter: HsvRangeFilterConfig, color: HsvColor) -> HsvRangeFilterConfig:
        log.debug(f'Setting filter {filter} ~ color {color}')
        c, r = color, filter.radius
        assert isinstance(r, tuple)
        filter.c0 = HsvColor(c[0]-r[0], c[1]-r[1], c[2]-r[2])
        filter.c1 = HsvColor(c[0]+r[0], c[1]+r[1], c[2]+r[2])

        return filter

    def mean_color(self, filter: HsvRangeFilterConfig) -> HsvColor:
        # todo: S and V are arbitrary for now
        return HsvColor(float(np.mean([filter.c0[0], filter.c1[0]])), 255.0, 200.0)

    def filter(self, img: np.ndarray, filter: HsvRangeFilterConfig) -> np.ndarray:
        return cv2.inRange(
            img, np.float32(filter.c0), np.float32(filter.c1), img
        )


FilterType.extend({
    'hsv range':    HsvRangeFilter,
})


class FilterHandler(BackendInstance, DynamicHandler):
    _implementation: FilterInterface
    _implementation_factory = FilterType
    _implementation_class = FilterInterface

    _config: FilterHandlerConfig
    _default = FilterHandlerConfig()

    def __init__(self, config: FilterHandlerConfig = None):
        super(FilterHandler, self).__init__(config)
        self.set_implementation(self._config.type)
        if self._config.data is None:
            self._config.data = self._implementation._config_class()

    @backend.expose(backend.get_filter_mean_color)
    def mean_color(self) -> HsvColor:
        return self._implementation.mean_color(self._config.data)

    @backend.expose(backend.set_filter_parameters)
    def set_filter(self, filter: FilterConfig, color: HsvColor) -> FilterConfig:
        self._config.data = self._implementation.set_filter(filter, color)
        assert isinstance(self._config.data, FilterConfig)
        return self._config.data

    @backend.expose(backend.get_filter_parameters)
    def get_filter(self) -> FilterConfig:
        assert isinstance(self._config.data, FilterConfig)
        return self._config.data

    @backend.expose(backend.set_filter_implementation)
    def set_implementation(self, implementation: str) -> str:
        return super(FilterHandler, self).set_implementation(implementation)

    @backend.expose(backend.filter)
    def __call__(self, frame: np.ndarray) -> np.ndarray:
        assert isinstance(self._config.data, FilterConfig)
        return self._implementation.filter(frame, self._config.data)



class Mask(BackendInstance):
    """Handles masks in the context of a video file
    """

    filter: FilterHandler

    _config: MaskConfig

    def __init__(self, mask: np.ndarray, name: str, config: MaskConfig = None, filter: FilterHandler = None):
        if config is None:
            config = MaskConfig()

        super(Mask, self).__init__(config)
        self._full = mask
        self._config.name = name

        self._full = mask
        self._part, self._rect, self._center = crop_mask(self._full)

        # Each Mask should have its own FilterHandler instance, unless otherwise specified
        if filter is None:
            if self._config.filter is not None:
                assert isinstance(self._config.filter, FilterHandlerConfig)
            filter = FilterHandler(self._config.filter)
            assert isinstance(filter, FilterHandler), BackendSetupError
        self.filter = filter
        self._config.filter = self.filter._config

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
        return img[self.rows, self.cols]

    @property
    def rows(self):
        return slice(self._rect[0], self._rect[1])

    @property
    def cols(self):
        return slice(self._rect[2], self._rect[3])

    @property
    def name(self):
        return self._config.name




class DesignFileHandler(CachingBackendInstance):
    _overlay: np.ndarray
    _masks: List[Mask]

    _config: DesignFileHandlerConfig
    _default = DesignFileHandlerConfig()

    def __init__(self, path: str, config: DesignFileHandlerConfig = None, mask_config: Tuple[MaskConfig,...] = None):
        super(DesignFileHandler, self).__init__(config)

        if not os.path.isfile(path):
            raise FileNotFoundError

        self._path = path
        with self.caching():  # todo: maybe also do this in a separate thread? It's quite slow.
            self._overlay = self.peel_design(path)
            self._shape = (self._overlay.shape[1], self._overlay.shape[0])

            self._masks = []
            for i, (mask, name) in enumerate(zip(*self.read_masks(path))):
                if mask_config is not None and len(mask_config) >= i+1:  # handle case len(mask_config) < len(self.read_masks(path))
                    self._masks.append(Mask(mask, name, mask_config[i]))
                else:
                    self._masks.append(Mask(mask, name))

    def _clear_renders(self):
        log.debug(f'Clearing render directory {self._config.render_dir}')
        renders = [f for f in os.listdir(self._config.render_dir)]
        for f in renders:
            os.remove(os.path.join(self._config.render_dir, f))

    def _peel_design(self, design_path) -> np.ndarray:
        if not os.path.isdir(self._config.render_dir):
            os.mkdir(self._config.render_dir)
        else:
            self._clear_renders()

        check_svg(design_path)
        OnionSVG(design_path, dpi=self._config.dpi).peel(
            'all', to=self._config.render_dir  # todo: should maybe prepend file name to avoid overwriting previous renders?
        )
        print("\n")

        overlay = cv2.imread(
            os.path.join(self._config.render_dir, 'overlay.png')
        )

        return overlay

    def _read_masks(self, _) -> Tuple[List[np.ndarray], List[str]]:
        files = os.listdir(self._config.render_dir)
        files.remove('overlay.png')

        # Catch file names of numbered layers
        pattern = re.compile('(\d+)[?\-=_#/\\\ ]+([?\w\-=_#/\\\ ]+)')

        sorted_files = []
        matched = {}
        mismatched = []

        for path in files:
            match = pattern.search(os.path.splitext(path)[0])
            path = os.path.join(self._config.render_dir, path)

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
            masks.append(
                to_mask(
                    cv2.imread(path), ckernel(self._config.smoothing)
                )
            )

            match = pattern.search(path)
            if match:
                names.append(match.groups()[1].strip())
            else:
                names.append(path)

        if not self._config.keep_renders:
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
        return self._config.dpi

    @backend.expose(backend.get_overlay)
    def overlay(self) -> np.ndarray:
        return self._overlay

    @backend.expose(backend.overlay_frame)
    def overlay_frame(self, frame: np.ndarray) -> np.ndarray:
        frame = cv2.cvtColor(frame, cv2.COLOR_HSV2BGR)
        frame = self._overlay_bgr(frame)
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        return frame

    def _overlay_bgr(self, frame: np.ndarray) -> np.ndarray:
        # https://stackoverflow.com/questions/54249728/
        return cv2.addWeighted(
            self._overlay, self._config.overlay_alpha,
            frame, 1 - self._config.overlay_alpha,
            gamma=0, dst=frame
        )

    @property
    def masks(self):
        return self._masks

    @backend.expose(backend.get_mask_names)
    def get_mask_names(self) -> tuple:
        return tuple(mask.name for mask in self._masks)


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

    def _guideline_color(self) -> HsvColor:
        return self.filter.mean_color()

    def value(self, frame) -> Any:
        return self._function(self.filter(self.mask(frame)))

    def state(self, frame: np.ndarray, state: np.ndarray = None) -> np.ndarray:
        """Generate a state image (BGR)
        """
        if state is not None:
            binary = self.filter(self.mask(frame))
            substate = np.multiply(
                np.ones((binary.shape[0], binary.shape[1], 3), dtype=np.uint8),
                cv2.cvtColor(np.uint8([[self.color]]), cv2.COLOR_HSV2BGR)
            )
            state[self.mask.rows, self.mask.cols, :] = cv2.bitwise_and(substate, substate, mask=binary)
            return state

    @property
    def name(self) -> str:
        return self.mask.name


class PixelSum(MaskFilterFunction):
    _function = staticmethod(area_pixelsum)  # todo: would be cleaner if we wouldn't need to have staticmethod here :/


VideoFeatureType.extend({
    'pixel sum':    PixelSum
})


class VideoAnalyzer(BackendManager):
    """Main video handling class
            * Load frames from video files
            * Load mask files
            * Load/save measurement metadata
    """
    _config: VideoAnalyzerConfig
    _default = VideoAnalyzerConfig('', '')
    _gui: Optional[Manager]
    _endpoints: BackendEndpoints = backend

    video: VideoFileHandler
    design: DesignFileHandler
    transform: TransformHandler
    features: Tuple[Feature,...]

    _featuresets: Dict[str, FeatureSet]
    value: Dict[str, pd.DataFrame]

    def __init__(self, config: VideoAnalyzerConfig = None):  # todo: add optional feature list to override self._config.features
        super(VideoAnalyzer, self).__init__(config)
        self.value = {}
        self._gather_instances()

    def _can_launch(self):
        if not (self._config.video_path is None and self._config.design_path is None):
            return os.path.isfile(self._config.video_path) \
                   and os.path.isfile(self._config.design_path)

    def _launch(self):
        self.load_config()
        log.debug(f'{self.__class__.__name__}: launch nested instances.')
        self.video = VideoFileHandler(self._config.video_path, self._config.video)
        self.video.set_requested_frames(list(self.frame_numbers()))
        self.design = DesignFileHandler(self._config.design_path, self._config.design, self._config.masks)
        self.transform = TransformHandler(self.design.shape, self._config.transform)
        self.masks = self.design.masks
        self.filters = [mask.filter for mask in self.masks]

        # todo: maybe add some stuff to do this automagically
        backend.expose(backend.get_frame)(self.get_transformed_frame)
        backend.expose(backend.get_inverse_transformed_overlay)(self.get_inverse_transformed_overlay)
        backend.expose(backend.get_overlaid_frame)(self.get_frame_overlay)
        backend.expose(backend.get_colors)(self.get_colors)

    def _get_featuresets(self):
        self._featuresets = {
            str(feature): FeatureSet(
                tuple(feature.get()(mask) for mask in self.design.masks),
            ) for feature in self._config.features
        }

        for fs, feature in zip(self._featuresets.values(), self._config.features):
            self.value[str(feature)] = pd.DataFrame(
                [], columns=['time'] + [f.name for f in fs.features], index=list(self.frame_numbers())
            )


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
        return str(self._config.video_path)

    @backend.expose(backend.get_h)
    def get_h(self) -> float:
        return float(self._config.height)

    @backend.expose(backend.get_config)
    def get_config(self) -> dict:
        return self._config.to_dict()

    @backend.expose(backend.set_config)  # todo: this is more complex now! Should only write values, not whole config.
    def set_config(self, config: dict) -> None:
        log.debug(f"Setting VideoAnalyzerConfig to {config}")
        self._configure(VideoAnalyzerConfig(**config))  # todo: make sure that this doesn't set the attributes that **aren't** not provided to the defaults!

    #@backend.expose(backend.get_frame)  # todo: nested methods, a bit ugly (:
    def get_transformed_frame(self, frame_number: int) -> np.ndarray:
        return self.transform(self.video.read_frame(
            frame_number))  # todo: depending on self.frame is dangerous in case we want to run this in a different thread

    #@backend.expose(backend.get_inverse_transformed_overlay)
    def get_inverse_transformed_overlay(self) -> np.ndarray:
        return self.transform.inverse(self.design.overlay())

    #@backend.expose(backend.get_overlaid_frame)
    def get_frame_overlay(self, frame_number: int) -> np.ndarray:
        return self.design.overlay_frame(
            self.get_transformed_frame(frame_number))

    #@backend.expose(backend.get_colors)  # todo: per feature in each feature set; maybe better as a dict instead of a list of tuples?
    def get_colors(self) -> List[Tuple[HsvColor, ...]]:
        return [featureset.get_colors() for featureset in
                self._featuresets.values()]

    def frame_numbers(self) -> Generator[int, None, None]:
        if self._config.frame_interval_setting == FrameIntervalSetting('Nf'):
            return frame_number_iterator(self.video.frame_count, Nf = self._config.Nf)
        elif self._config.frame_interval_setting == FrameIntervalSetting('dt'):
            return frame_number_iterator(self.video.frame_count, dt = self._config.dt, fps = self.video.fps)
        else:
            raise ValueError(f"Unexpected frame interval setting "
                             f"{self._config.frame_interval_setting}")

    def calculate(self, frame_number: int, update_callback: Callable):
        """Return a state image for each FeatureSet
        """
        t = self.video.get_time(frame_number)
        raw_frame = self.video.read_frame(frame_number)
        frame = self.transform(raw_frame)

        V = []
        S = []
        for k,fs in self._featuresets.items():  # todo: for each feature set -- export data for a separate legend to add to the state plot
            values = []
            state = np.zeros(frame.shape, dtype=np.uint8)  # BGR state image
            # todo: may be faster / more memory-efficient to keep state[i] and set it to 0

            for feature in fs._features:  # todo: make featureset iterable maybe
                value, state = feature.calculate(
                    frame.copy(),  # don't overwrite self.frame ~ cv2 dst parameter  # todo: better to let OpenCV handle copying, or not?
                    state               # additive; each feature adds to state
                )
                values.append(value)

            state[np.equal(state, 0)] = 255

            # Add overlay on top of state
            state = self.design._overlay_bgr(state)

            V.append(values)   # todo: value values value ugh
            S.append(state)

            self.value[k].loc[frame_number] = [t] + values

        update_callback(
            t,
            V, # todo: this is per feature in each feature set; maybe better as dict instead of list of lists?
            S,     # todo: keep values (in order to save them)
            frame
        )

    def analyze(self):
        self._get_featuresets()
        self.save_config()
        if self._gui is not None:
            update_callback = self._gui.get(gui.update_progresswindow)
            self._gui.get(gui.open_progresswindow)()
        else:
            def update_callback(*args, **kwargs): pass

        for fn in self.frame_numbers():
            self.calculate(fn, update_callback)

        self.save()

    def load_config(self, path: str = None):
        """Load video analysis configuration
        """
        if path is None and self._config.video_path:
            path = self._config.video_path

        if path is not None:
            path = os.path.splitext(path)[0] + __meta_ext__
            if os.path.isfile(path):
                self._config = load(path)
        else:
            log.warning(f"No path provided to `load_config`; no video file either.")

    def save_config(self, path: str = None):
        """Save video analysis configuration
        """
        if path is None and self._config.video_path:
            path = self._config.video_path

        if path is not None:
            path = os.path.splitext(path)[0] + __meta_ext__
            dump(self._gather_config(), path)
        else:
            log.warning(f"No path provided to `save_config`; no video file either.")

    def _gather_config(self) -> VideoAnalyzerConfig:
        """Gather configuration from instances
        """
        self._config.video = self.video._config
        self._config.design = self.design._config
        self._config.transform = self.transform._config
        self._config.masks = tuple(
            [m._config for m in self.masks]
        )
        return self._config

    def save(self, path: str = None):
        """Save video analysis results & metadata
        """
        name = str(os.path.splitext(self._config.video_path)[0])  # type: ignore
        f = name + ' ' + datetime.datetime.now().strftime("%Y-%m-%d %H-%M-%S") + '.xlsx'

        w = pd.ExcelWriter(f)
        for k,v in self.value.items():
            v.to_excel(w, sheet_name=k)

        pd.DataFrame([dumps(self._config)]).to_excel(w, sheet_name='meta')

        w.save()
        w.close()


class MultiVideoAnalyzer(BackendManager):
    pass


BackendType.extend({
    'VideoAnalyzer': VideoAnalyzer,
})
