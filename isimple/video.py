import re
import os
from typing import Any, Callable

import cv2

from OnionSVG import OnionSVG, check_svg

from isimple.core.util import *
from isimple.core.common import Manager
from isimple.core.backend import BackendInstance, CachingBackendInstance, DynamicHandler, BackendManager, BackendSetupError
from isimple.core.features import Feature, FeatureSet
from isimple.core.config import *
from isimple.core.config import Color

from isimple.maths.images import to_mask, crop_mask, area_pixelsum

from isimple.endpoints import BackendEndpoints
from isimple.endpoints import GuiEndpoints as gui


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

    def set_requested_frames(self, allowed_frames: List[int]) -> None:
        """Add a list of requested frames.
            Used to determine which frames to cache in the background and
            in `_resolve_frame`
        """
        self._requested_frames = allowed_frames

    def _resolve_frame(self, frame_number: int) -> int:
        """Resolve a frame_number to the nearest requested frame number
            This is used to limit the polled frames to the
            frames that are to be cached or are cached already.
        """
        if hasattr(self, '_allowed_frames'):
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

    @abc.abstractmethod
    def inverse_transform(self, img: np.ndarray, transform: np.ndarray, shape: tuple):
        raise NotImplementedError


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


TransformType.extend({
    'perspective': PerspectiveTransform,
})


class TransformHandler(BackendInstance, DynamicHandler):
    """Handles coordinate transforms.
    """
    _shape: tuple
    _transform: Optional[np.ndarray]

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

        self._transform = None
        if self._config.matrix is not None:
            self.set(self._config.matrix)
        else:
            self.set(self._implementation.default)

    @backend.expose(backend.set_transform_implementation)
    def set_implementation(self, implementation: str) -> str:
        # If there's ever any method to set additional transform options, this method/endpoint can be merged into that
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

    @abc.abstractmethod
    def set_filter(self, filter, color: Color):
        raise NotImplementedError

    @abc.abstractmethod
    def mean_color(self, filter) -> Color:  # todo: add custom np.ndarray type 'hsvcolor'
        raise NotImplementedError

    @abc.abstractmethod
    def filter(self, image: np.ndarray, filter) -> np.ndarray:  # todo: add custom np.ndarray type 'image'
        raise NotImplementedError


class HsvRangeFilter(FilterInterface):  # todo: may be better to **wrap** this in Filter instead of inheriting from it
    """Filters by a range of hues ~ HSV representation
    """
    _default = HsvRangeFilterConfig()

    def validate(self, filter):  # todo: may be better to 'normalize' the filter dict -- i.e. replace all fields that weren't found with the defaults
        return all(attr in self._default for attr in filter)

    def set_filter(self, filter: HsvRangeFilterConfig, color: Color) -> HsvRangeFilterConfig:
        c, r = color, filter.radius
        assert isinstance(r, tuple)
        filter.c0 = (c[0]-r[0], c[1]-r[1], c[2]-r[2])
        filter.c1 = (c[0]+r[0], c[1]+r[1], c[2]+r[2])

        return filter

    def mean_color(self, filter: HsvRangeFilterConfig) -> Color:
        # todo: S and V are arbitrary for now
        return (float(np.mean([filter.c0[0], filter.c1[0]])), 255.0, 200.0)

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

    @backend.expose(backend.get_filter_mean_color)
    def mean_color(self) -> Color:
        return self._implementation.mean_color(self._config.filter)

    @backend.expose(backend.set_filter_parameters)
    def set_filter(self, filter: FilterConfig, color: Color) -> FilterConfig:
        self._config.filter = self._implementation.set_filter(filter, color)
        assert isinstance(self._config.filter, FilterConfig)
        return self._config.filter

    @backend.expose(backend.get_filter_parameters)
    def get_filter(self) -> FilterConfig:
        assert isinstance(self._config.filter, FilterConfig)
        return self._config.filter

    @backend.expose(backend.set_filter_implementation)
    def set_implementation(self, implementation: str) -> str:
        return super(FilterHandler, self).set_implementation(implementation)

    @backend.expose(backend.filter)
    def __call__(self, frame: np.ndarray) -> np.ndarray:
        assert isinstance(self._config.filter, FilterConfig)
        return self._implementation.filter(frame, self._config.filter.to_dict())



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
        self.name = name

        self._full = mask
        self._part, self._rect, self._center = crop_mask(self._full)

        # Each Mask should have its own FilterHandler instance, unless otherwise specified
        if filter is None:
            if self._config.filter is not None:
                assert isinstance(self._config.filter, FilterHandlerConfig)
            filter = FilterHandler(self._config.filter)
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
                if mask_config is not None:
                    self._masks.append(Mask(mask, name, mask_config[i]))
                else:
                    self._masks.append(Mask(mask, name))

    def _clear_renders(self):
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
            masks.append(to_mask(cv2.imread(path), self._config.smoothing_kernel))

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
        frame = cv2.addWeighted(
            self._overlay, self._config.overlay_alpha,  # https://stackoverflow.com/questions/54249728/
            frame, 1 - self._config.overlay_alpha,
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

    _featuresets: List[FeatureSet]

    def __init__(self, config: VideoAnalyzerConfig = None):  # todo: add optional feature list to override self._config.features
        super(VideoAnalyzer, self).__init__(config)
        self._gather_instances()

    @timing
    def launch(self):
        # todo: better sanity check -- are we already launched maybe?
        video_path = self._config.video_path
        design_path = self._config.design_path

        if os.path.isfile(video_path) and os.path.isfile(design_path):
            self.video = VideoFileHandler(video_path, self._config.video)
            self.video.set_requested_frames(list(self.frame_numbers()))
            self.design = DesignFileHandler(design_path, self._config.design)
            self.transform = TransformHandler(self.design.shape, self._config.transform)
            self.masks = self.design.masks
            self.filters = [mask.filter for mask in self.masks]

            self._gather_instances()  # todo: annoying that we have to call this one explicilty, but doing it at super.__init__ makes it less dynamic
        else:
            raise ValueError("Either the video or the design wasn't provided")  # todo: make error message more specific

    def _get_featuresets(self):
        self._featuresets = [
            FeatureSet(
                tuple(feature.get()(mask) for mask in self.design.masks)
            ) for feature in self._config.features
        ]

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
        return self._config.to_dict()

    @backend.expose(backend.get_h)
    def get_h(self) -> float:
        return self._config.height

    @backend.expose(backend.set_config)  # todo: this is more complex now! Should only write values, not whole config.
    def set_config(self, config: dict) -> None:
        self._configure(VideoAnalyzerConfig(**config))  # todo: make sure that this doesn't set the attributes that **aren't** not provided to the defaults!

    @backend.expose(backend.set_video_path)
    def set_video_path(self, video_path: str) -> None:
        self._config.video_path = video_path

    @backend.expose(backend.set_design_path)
    def set_design_path(self, design_path: str) -> None:
        self._config.design_path = design_path

    def frame_numbers(self) -> Generator[int, None, None]:
        if self._config.frame_interval_setting == FrameIntervalSetting('Nf'):
            return frame_number_iterator(self.video.frame_count, Nf = self._config.Nf)
        elif self._config.frame_interval_setting == FrameIntervalSetting('dt'):
            return frame_number_iterator(self.video.frame_count, dt = self._config.dt, fps = self.video.fps)
        else:
            raise ValueError(f"Unexpected frame interval setting "
                             f"{self._config.frame_interval_setting}")

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
    def get_colors(self) -> List[Tuple[Color,...]]:
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
            S,     # todo: keep values (in order to save them)
            frame
        )

    def analyze(self):
        self._get_featuresets()
        if self._gui is not None:
            update_callback = self._gui.get(gui.update_progresswindow)
            self._gui.get(gui.open_progresswindow)()
        else:
            def update_callback(*args, **kwargs): pass

        for fn in self.frame_numbers():
            self.calculate(fn, update_callback)


    def load_config(self, path: str):
        """Load video analysis configuration
        """
        self._config = load(path)
        self.launch()

    def save_config(self, path: str):
        """Save video analysis configuration
        """
        dump(self._gather_config(), path)

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

    def save(self):
        """Save video analysis results & metadata
        """

        config_yaml =

        raise NotImplementedError


class MultiVideoAnalyzer(BackendManager):
    pass