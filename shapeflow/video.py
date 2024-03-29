import os
import re
import abc
import threading
import copy
from typing import Callable, Any, Dict, Generator, Optional, List, Tuple, Type

import cv2
import numpy as np
import pandas as pd

from shapeflow import get_logger, settings, ResultSaveMode
from shapeflow.api import api
from shapeflow.config import VideoFileHandlerConfig, TransformHandlerConfig, \
    FilterHandlerConfig, MaskConfig, \
    DesignFileHandlerConfig, VideoAnalyzerConfig, \
    FrameIntervalSetting, BaseAnalyzerConfig, FlipConfig
from shapeflow.core import Lockable, RootException
from shapeflow.core.backend import Instance, CachingInstance, \
    BaseAnalyzer, BackendSetupError, AnalyzerType, Feature, \
    FeatureSet, \
    FeatureType, AnalyzerState, PushEvent, FeatureConfig, CacheAccessError
from shapeflow.core.config import extend
from shapeflow.core.interface import TransformInterface, FilterConfig, \
    FilterInterface, FilterType, TransformType, Handler
from shapeflow.core.streaming import stream, streams
from shapeflow.design import peel
from shapeflow.maths.colors import Color, HsvColor, BgrColor, convert, css_hex
from shapeflow.maths.images import to_mask, crop_mask, ckernel, \
    overlay, rect_contains
from shapeflow.maths.coordinates import ShapeCoo, Roi
from shapeflow.util import frame_number_iterator

log = get_logger(__name__)


class VideoFileTypeError(BackendSetupError):
    msg = 'Unrecognized video file type'  # todo: formatting


class VideoFileHandler(CachingInstance, Lockable):
    """Interface to video files ~ ``OpenCV``
    """
    path: str
    """Path to the video file
    """

    frame_count: int
    fps: float
    frame_number: int
    _requested_frames: List[int]

    _capture: cv2.VideoCapture

    _shape: tuple

    colorspace: str

    _config: VideoFileHandlerConfig
    _config_class = VideoFileHandlerConfig
    _class = VideoFileHandlerConfig()

    _progress_callback: Callable[[float], None]

    def __init__(self, video_path, config: VideoFileHandlerConfig = None):
        super(VideoFileHandler, self).__init__(config)
        self._is_caching = False

        if not os.path.isfile(video_path):
            raise FileNotFoundError

        self.path = video_path
        self._cached = False

        self._capture = cv2.VideoCapture(
            os.path.join(os.getcwd(), self.path)
        )  # todo: handle failure to open capture

        self.frame_count = int(self._capture.get(cv2.CAP_PROP_FRAME_COUNT))  # todo: should be 'private' attributes
        self.fps = self._capture.get(cv2.CAP_PROP_FPS)
        self.frame_number = int(self._capture.get(cv2.CAP_PROP_POS_FRAMES))

        self._shape = tuple([
            int(self._capture.get(cv2.CAP_PROP_FRAME_WIDTH)),
            int(self._capture.get(cv2.CAP_PROP_FRAME_HEIGHT)),
        ])

        if self.frame_count == 0:
            raise VideoFileTypeError

    @property
    def config(self) -> VideoFileHandlerConfig:
        return self._config

    @property
    def shape(self):
        return self._shape
    
    @property
    def cached(self):
        return self._cached

    def _check_cached(self) -> Optional[bool]:
        try:
            self._cached = all([
                self._is_cached(self._read_frame, self.path, fn)
                for fn in self._requested_frames
            ])
            return self._cached
        except CacheAccessError:
            return None

    def set_requested_frames(self, requested_frames: List[int]) -> None:
        """Add a list of requested frames

        Limiting the set of possible frames decreases the disk space cost
        needed to get a performance advantage through caching.
        """
        log.debug(f"Requested frames: {requested_frames}")
        self._requested_frames = requested_frames

        self._check_cached()
        # self._touch_keys(
        #     [self._get_key(self._read_frame, self.path, fn)
        #      for fn in requested_frames]
        # )

    def _resolve_frame(self, frame_number) -> int:
        """Resolve a frame_number to the nearest requested frame number

        This is done in order to limit the polled frames to the
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
        """Set the position of the ``cv2.VideoCapture``.
        """
        self._capture.set(cv2.CAP_PROP_POS_FRAMES, frame_number)
        self._get_position()

    def _get_position(self) -> int:
        """Get the position of the ``cv2.VideoCapture``.

        Due to some internal workings of OpenCV, the actual position the
        capture object ends up at may differ from the requested position.
        """
        self.frame_number = self._capture.get(cv2.CAP_PROP_POS_FRAMES)
        return self.frame_number

    def _read_frame(self, _: str, frame_number: int = None) -> Optional[np.ndarray]:
        """Read frame from video file, HSV color space

        The `_` parameter is a placeholder for the (unused) path of the
        video file, which is used to make the cache key in order to make
        this function cachable across multiple files.
        """
        with self.lock():
            if frame_number is None:
                frame_number = self.frame_number

            log.debug(f"reading  {self.path} frame {self.frame_number}")

            self._set_position(frame_number)
            ret, frame = self._capture.read()

            if ret:
                frame = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV, frame)
                return frame
            else:
                log.warning(f"could not read {self.path} frame {self.frame_number}")
                return None

    def get_time(self, frame_number: int = None) -> float:
        if frame_number is None:
            frame_number = self.frame_number

        return self._resolve_frame(frame_number) / self.fps

    def get_fps(self) -> float:
        return self.fps

    def get_total_time(self) -> float:
        return self.frame_count / self.fps

    def read_frame(self, frame_number: Optional[int] = None) -> np.ndarray:
        """Read a frame from ``cv2.VideoCapture``.
        """
        if frame_number is None:
            frame_number = self.frame_number

        if settings.cache.resolve_frame_number:
            frame_number = self._resolve_frame(frame_number)

        return self.cached_call(self._read_frame, self.path, frame_number)

    def seek(self, position: float = None) -> float:
        """Seek to a relative position in the video ~ [0,1]
        """
        # todo: had to remove lock to enable reading frames :/
        #       (otherwise streams.update() can get deadocked @ VideoFileHandler if not reading frames from cache)
        if position is not None:
            frame_number = int(position * self.frame_count)
            if settings.cache.resolve_frame_number:
                self.frame_number = self._resolve_frame(frame_number)
            else:
                self.frame_number = frame_number

        log.debug(f"seeking  {self.path} {self.frame_number}/{self.frame_count}")
        streams.update()

        return self.frame_number / self.frame_count

    def get_seek_position(self) -> float:
        """Get current relative position in the video ~ [0,1]
        """
        return self.frame_number / self.frame_count


class NotEstimatedYet(RootException):
    msg = "Transform has not been estimated yet"


class TransformHandler(Instance, Handler):  # todo: clean up config / config.data -> Handler should not care what goes on in config.data!
    """Handles coordinate transforms
    """
    _video_shape: Tuple[int, int]
    _design_shape: Tuple[int, int]

    _implementation: TransformInterface
    _implementation_factory = TransformType
    _implementation_class = TransformInterface

    _config: TransformHandlerConfig
    _config_class = TransformHandlerConfig

    _matrix: Optional[np.ndarray]
    _inverse: Optional[np.ndarray]

    def __init__(self, video_shape, design_shape, config: TransformHandlerConfig):
        super(TransformHandler, self).__init__(config)
        self.set_implementation(self.config.type.__str__())
        self._video_shape = (video_shape[0], video_shape[1])  # Don't include color dimension
        self._design_shape = (design_shape[0], design_shape[1])

        self.estimate(self.config.roi)

    @property
    def config(self) -> TransformHandlerConfig:
        return self._config

    def set_implementation(self, implementation: str = None) -> str:
        # If there's ever any method to set additional transform options, this method/endpoint can be merged into that
        if implementation is None:
            implementation = self.config.type
        return super(TransformHandler, self).set_implementation(implementation)

    def set(self, matrix: Optional[np.ndarray]):
        """Set the transform matrix
        """
        if matrix is not None:
            if self._implementation.validate(matrix):
                self._matrix = matrix
                self._inverse = self._implementation.invert(matrix)
            else:
                raise ValueError(f"Invalid transform {matrix} for "
                                 f"'{self._implementation.__class__.__name__}'")
        else:
            self._matrix = None
            self._inverse = None

    @property
    def is_set(self) -> bool:
        """Whether the transform matrix is set
        """
        if hasattr(self, '_matrix'):
            return self._matrix is not None
        else:
            return False

    def get_relative_roi(self) -> dict:
        """Get the relative ROI as a ``dict``
        """
        if self.config.roi is not None:
            try:
                return {
                    k: {
                        'x': v['x'],
                        'y': v['y']
                    } for k,v in self.config.roi.dict().items()
                }
            except KeyError:
                return {}
        else:
            return {}

    def estimate(self, roi: Roi = None) -> None:
        """Estimate the transform matrix from a set of coordinates.

        Coordinates should correspond to the corners of the outline of
        the design, relative to the video frame size:
        * x in [0,1] ~ width
        * y in [0,1] ~ height
        """
        # todo: sanity check roi

        if roi is not None:
            self.config(roi=roi)

            self.set(self._implementation.estimate(self._adjust(roi), self._video_shape, self._design_shape))
            streams.update()

    def _adjust(self, roi: Roi) -> Roi:
        """Adjust ROI (90° turns & flips)
        """
        # Don't adjust roi in config!
        roi = copy.deepcopy(roi)

        # Flip
        if self.config.flip.vertical and not self.config.flip.horizontal:
            # Flip vertically
            roi(
                BL=roi.TL,
                TL=roi.BL,
                BR=roi.TR,
                TR=roi.BR
            )
        elif self.config.flip.horizontal and not self.config.flip.vertical:
            # Flip horizontally
            roi(
                BL=roi.BR,
                TL=roi.TR,
                BR=roi.BL,
                TR=roi.TL
            )
        elif self.config.flip.horizontal and self.config.flip.vertical:
            # Flip both (180° rotation)
            roi(
                BL=roi.TR,
                TL=roi.BR,
                BR=roi.TL,
                TR=roi.BL
            )

        # Turn
        if self.config.turn != 0:
            self.config(turn = self.config.turn % 4)

            corners = ['TR', 'BR', 'BL', 'TL',]
            turnedc = ['TL', 'TR', 'BR', 'BL',]
            cw_90d_map = {c:t for c,t in zip(corners, turnedc)}

            cw_turn_map = {c:c for c in corners}
            for _ in range(self.config.turn):
                cw_turn_map = {k:cw_90d_map[v] for k,v in cw_turn_map.items()}

            roi(**{cw_turn_map[k]:v for k,v in roi.dict().items()})

        return roi

    def clear(self) -> None:
        """Clear the ROI
        """
        self.config(roi=None)
        self.set(None)

        streams.update()

    def get_coordinates(self) -> Optional[list]:
        if isinstance(self.config.roi, list):
            return self.config.roi
        else:
            return None

    def __call__(self, img: np.ndarray) -> np.ndarray:
        """Transform an image

        .. note::
           Writes to the provided variable!
           If caller needs the original value, they should copy explicitly.
        """
        if self._matrix is not None:
            return self._implementation.transform(self._matrix, img, self._design_shape)
        else:
            raise NotEstimatedYet()

    def coordinate(self, coordinate: ShapeCoo) -> Optional[ShapeCoo]:
        """Transform a design coordinate to a video coordinate
        """
        if self._inverse is not None:
            co = self._implementation.coordinate(
                self._inverse, coordinate, self._video_shape[::-1]
            )
            return co
        else:
            raise NotEstimatedYet()

    def inverse(self, img: np.ndarray) -> np.ndarray:
        """Inverse transform an image
        """
        if self._inverse is not None:
            return self._implementation.transform(self._inverse, img, self._video_shape)
        else:
            raise NotEstimatedYet()


class FilterHandler(Instance, Handler):
    """Handles filters
    """
    _implementation: FilterInterface
    _implementation_factory = FilterType
    _implementation_class = FilterInterface

    _config_class = FilterHandlerConfig
    _config: FilterHandlerConfig

    def __init__(self, config: FilterHandlerConfig = None):
        super(FilterHandler, self).__init__(config)

        if config is not None:
            self._config = config
        else:
            self._config = FilterHandlerConfig()

        self.set_implementation()

    @property
    def config(self) -> FilterHandlerConfig:
        return self._config

    def set_config(self, config: dict) -> None:
        """Set the configuration of this filter
        """
        self._config(**config)
        self.set_implementation()

    @property
    def implementation(self):
        return self._implementation

    def mean_color(self) -> Color:
        return self.implementation.mean_color(self.config.data)

    def set(self, color: HsvColor = None) -> FilterConfig:
        """Set the filter to a color.
        """
        # if isinstance(self.config.data, dict):  todo: should be ok
        #     self.config.data = self.implementation.config_class()(**self.config.data)

        if color is None:
            color = HsvColor(0,0,0)

        self.config(data=self.implementation.set_filter(self.config.data, color))

        log.debug(f"Filter config: {self.config}")

        return self.config.data

    def set_implementation(self, implementation: str = None) -> str:
        """Set the filter implementation
        """
        if implementation is None:
            implementation = self.config.type.__str__()

        implementation = super(FilterHandler, self).set_implementation(implementation)

        # Keep matching config fields accross implementations
        old_data = self.config.data.to_dict()
        new_keys = list(self.implementation.config_class().__fields__.keys())

        self.config(
            type=implementation,
            data=self.implementation.config_class()(
                **{key:old_data[key] for key in new_keys if key in old_data}
            )
        )

        return implementation

    def __call__(self, frame: np.ndarray, mask: np.ndarray = None) -> np.ndarray:
        """Filter an image
        """
        return self.implementation.filter(self.config.data, frame, mask)


class Mask(Instance):
    """Handles masks in the context of a video file
    """
    filter: FilterHandler
    """The filter associated with this mask
    """

    _design: 'DesignFileHandler'

    _config_class = MaskConfig
    _config: MaskConfig
    _dpi: float

    _full: np.ndarray
    _part: np.ndarray
    _rect: np.ndarray
    _center: Tuple[int,int]

    def __init__(
            self,
            design: 'DesignFileHandler',
            mask: np.ndarray,
            name: str,
            config: MaskConfig = None,
            filter: FilterHandler = None,
    ):
        if config is None:
            config = MaskConfig()

        super(Mask, self).__init__(config)

        self._design = design
        self._full = mask
        self.config(name=name)

        self._full = mask
        self._part, self._rect, self._center = crop_mask(self._full)

        # Each Mask should have its own FilterHandler instance, unless otherwise specified
        if filter is None:
            if self.config.filter is not None:
                assert isinstance(self.config.filter, FilterHandlerConfig)
            filter = FilterHandler(self.config.filter)
            assert isinstance(filter, FilterHandler), BackendSetupError
        self.filter = filter
        self.config(filter=self.filter.config)

    @property
    def config(self) -> MaskConfig:
        return self._config

    def set_config(self, config: dict) -> None:
        """Set the configuration of this mask
        """
        self._config(**config)
        self.filter.set_config(self.config.filter.to_dict())

    def set_filter(self, color: Optional[HsvColor]):
        """Set the filter of this mask
        """
        self.filter.set(color=color)
        self.config.filter(**self.filter.config.to_dict())  # todo: otherwise, mask config is not updated!

    def __call__(self, img: np.ndarray) -> np.ndarray:
        """Mask an image.

        .. note::
           Writes to the provided variable!
           If caller needs the original value, they should copy explicitly
        """
        img = self._crop(img)
        return cv2.bitwise_and(img, img, mask=self.part)

    def _crop(self, img: np.ndarray) -> np.ndarray:
        """Crop an image to fit self._part
        .. note::
           Writes to the provided variable!
           If caller needs the original value, they should copy explicitly
        """
        return img[self.rows, self.cols]

    def contains(self, coordinate: ShapeCoo) -> bool:
        """Whether a coordinate is contained within this mask
        """
        if rect_contains(self.rect, coordinate):
            return bool(
                self.part[coordinate.idx[0] - self.rect[0], coordinate.idx[1] - self.rect[2]]
            )
        else:
            return False

    def clear_filter(self):
        """Clear this mask's filter
        """
        self.set_filter(color=None)

    @property
    def design(self):
        return self._design

    @property
    def rows(self):
        """This mask's row slice

        To crop an image to this mask::

           crop = img[mask.rows, mask.cols]
        """
        return slice(self._rect[0], self._rect[1])

    @property
    def cols(self):
        """This mask's column slice

        To crop an image to this mask::

           crop = img[mask.rows, mask.cols]
        """
        return slice(self._rect[2], self._rect[3])

    @property
    def name(self):
        return self.config.name

    @property
    def part(self):
        return self._part

    @property
    def rect(self) -> np.ndarray:
        return self._rect

    @property
    def ready(self):
        return self.config.ready

    @property
    def skip(self):
        return self.config.skip


class DesignFileHandler(CachingInstance):
    """Handles design files
    """
    _overlay: np.ndarray
    _masks: List[Mask]

    _config: DesignFileHandlerConfig
    _config_class = DesignFileHandlerConfig

    def __init__(self, path: str, config: DesignFileHandlerConfig = None, mask_config: Tuple[MaskConfig,...] = None):
        super(DesignFileHandler, self).__init__(config)
        if not os.path.isfile(path):
            raise FileNotFoundError

        self._path = path
        self._render(path, mask_config)

    def _render(self, path: str = None, mask_config: Tuple[MaskConfig, ...] = None):
        if path is None:
            path = self._path

        self._overlay = self.peel_design(path, self.config.dpi)
        self._shape = (self._overlay.shape[1], self._overlay.shape[0])

        self._masks = []
        for i, (mask, name) in enumerate(zip(*self.read_masks(path, self.config.dpi))):
            if mask_config is not None and len(mask_config) > 0 and len(mask_config) >= i + 1:  # handle case len(mask_config) < len(self.read_masks(path))
                self._masks.append(
                    Mask(self, mask, name, mask_config[i])
                )
            else:
                self._masks.append(Mask(self, mask, name))

    @property
    def config(self) -> DesignFileHandlerConfig:
        return self._config

    def _clear_renders(self):
        log.debug(f'Clearing render directory {settings.render.dir}')
        renders = [f for f in os.listdir(settings.render.dir)]
        for f in renders:
            os.remove(os.path.join(settings.render.dir, f))

    def _peel_design(self, design_path, dpi) -> np.ndarray:
        if not os.path.isdir(settings.render.dir):
            os.mkdir(settings.render.dir)
        else:
            self._clear_renders()

        peel(design_path, dpi, settings.render.dir)

        overlay = cv2.imread(
            os.path.join(settings.render.dir, 'overlay.png')
        )

        return overlay

    def _read_masks(self, _, __) -> Tuple[List[np.ndarray], List[str]]:
        files = os.listdir(settings.render.dir)
        files.remove('overlay.png')

        # Catch file names of numbered layers
        pattern = re.compile(r'(\d+)[?\-=_#/\\\ ]+([?\w\-=_#/\\\ ]+)')

        sorted_files = []
        matched = {}
        mismatched = []

        for path in files:
            match = pattern.search(os.path.splitext(path)[0])
            path = os.path.join(settings.render.dir, path)

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
                    cv2.imread(path), ckernel(self.config.smoothing)
                )
            )

            match = pattern.search(path)
            if match:
                names.append(match.groups()[1].strip())
            else:
                names.append(path)

        if not settings.render.keep:
            self._clear_renders()

        return masks, names

    def peel_design(self, design_path: str, dpi: int) -> np.ndarray:
        """Render out all of the layers in a design
        """
        return self.cached_call(self._peel_design, design_path, dpi)

    def read_masks(self, design_path: str, dpi: int) -> Tuple[List[np.ndarray], List[str]]:
        """Load masks from the rendered files
        """
        return self.cached_call(self._read_masks, design_path, dpi)

    @property
    def shape(self):
        """The ``numpy.ndarray.shape`` of the design
        """
        return self._shape

    def overlay(self) -> np.ndarray:
        """The overlay of this design
        """
        return cv2.cvtColor(self._overlay, cv2.COLOR_BGR2HSV)

    def overlay_frame(self, frame: np.ndarray) -> np.ndarray:
        """Apply this design's overlay to a frame

        Parameters
        ----------
        frame: np.ndarray
            An image

        Returns
        -------
        np.ndarray
            The image with the overlay laid over it
        """
        frame = cv2.cvtColor(frame, cv2.COLOR_HSV2BGR)
        frame = overlay(frame, self._overlay, self.config.overlay_alpha)
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        return frame

    @property
    def masks(self) -> List[Mask]:
        """The masks of this design
        """
        return self._masks


class MaskFunction(Feature, metaclass=abc.ABCMeta):
    """An abstract feature based on a :class:`~shapeflow.video.Mask`
    """
    mask: Mask
    filter: FilterHandler  # todo: adress through mask
    dpi: int

    _feature_type: FeatureType

    def __init__(self, mask: Mask, global_config: FeatureConfig, config: Optional[dict] = None):
        self.mask = mask
        self.filter = mask.filter
        self.dpi = mask.design.config.dpi

        super(MaskFunction, self).__init__(
            (self.mask, self.filter), global_config, config
        )

        self._feature_type = FeatureType(self.__class__.__name__)

    @property
    def name(self):
        return self.mask.name

    @property
    def feature_type(self) -> FeatureType:
        return self._feature_type

    @property
    def ready(self) -> bool:
        return self.mask.config.ready

    @property
    def skip(self):
        return self.mask.config.skip

    def px2mm(self, value):
        """Convert design-space pixels to mm

        Parameters
        ----------
        value: float
            Distance in # of pixels

        Returns
        -------
        float
            Distance in mm
        """
        return value / (self.dpi / 25.4)

    def pxsq2mmsq(self, value):
        """Convert design-space pixels to mm²

        Parameters
        ----------
        value: float
            Area in pixels

        Returns
        -------
        float
            Area in mm²
        """
        return value / (self.dpi / 25.4) ** 2

    def _guideline_color(self) -> Color:
        return self.filter.mean_color()

    def value(self, frame) -> Any:
        """The value of this feature for a given frame

        Parameters
        ----------
        frame
            An image

        Returns
        -------
        Any
            Some value
        """
        return self._function(self.filter(self.mask(frame), self.mask.part))

    def state(self, frame: np.ndarray, state: np.ndarray) -> np.ndarray:
        """Generate a state image (BGR)
        """
        if not self.skip:
            if self.ready:
                # Masked & filtered pixels ~ frame
                binary = self.filter(self.mask(frame), self.mask.part)

                substate = np.multiply(
                    np.ones((binary.shape[0], binary.shape[1], 3),
                            dtype=np.uint8),
                    convert(self.color, BgrColor).np3d
                )
                state[self.mask.rows, self.mask.cols, :] \
                    += cv2.bitwise_and(substate, substate, mask=binary)
            else:
                # Not ready -> highlight feature with a rectangle
                substate = np.zeros((*self.mask.part.shape, 3), dtype=np.uint8)

                for i,c in enumerate(convert(self.color, BgrColor).list):  # todo: numpy this
                    substate[0:2, :, i] = c
                    substate[-2:, :, i] = c
                    substate[:, 0:2, i] = c
                    substate[:, -2:, i] = c

                state[self.mask.rows, self.mask.cols, :] += substate

              # todo: overwrites rect with white
        return state

    @abc.abstractmethod
    def _function(self, frame: np.ndarray) -> Any:
        """The function to apply to each masked and filtered frame
        """


@extend(AnalyzerType)
class VideoAnalyzer(BaseAnalyzer):
    """Main video handling class

            * Load frames from video files

            * Load mask files

            * Load/save measurement metadata
    """
    _config: VideoAnalyzerConfig
    _config_class = VideoAnalyzerConfig
    # _endpoints: BackendRegistry = backend

    video: VideoFileHandler
    """Handles video operations for this analyzer
    
    * Reads frames from the video file
    """
    design: DesignFileHandler
    """Handles design operations for this analyzer.
    
    * Renders the design
    
    * Reads in the overlay and mask images
    
    * Initializes the :class:`~shapeflow.video.Mask` instances
    """
    transform: TransformHandler
    """Handles the transform for this analyzer
    """
    features: Tuple[Feature,...]
    """The features used in this analysis
    """
    results: Dict[str, pd.DataFrame]
    """The results of the current run of this analysis
    """

    _featuresets: Dict[FeatureType, FeatureSet]

    def __init__(self, config: VideoAnalyzerConfig = None):
        super().__init__(config)
        self.results: Dict[FeatureType, pd.DataFrame] = {}

    @property
    def config(self) -> VideoAnalyzerConfig:
        return self._config

    def _gather_config(self):
        # todo: would be nice if this wasn't necessary :(
        if hasattr(self, 'video') and self.config.video != self.video.config:
            self.config(video=self.video.config)
        if hasattr(self, 'design') and self.config.design != self.design.config:
            self.config(design=self.design.config)
        if hasattr(self, 'transform') and self.config.transform != self.transform.config:
            self.config(transform=self.transform.config)
        if hasattr(self, 'masks'):
            self.config(masks=tuple([mask.config for mask in self.masks]))

    @property
    def cached(self) -> bool:
        if hasattr(self, 'video'):
            return self.video.cached
        else:
            return False

    @property
    def has_results(self) -> bool:
        return hasattr(self, 'results')

    @api.va.__id__.can_launch.expose()
    def can_launch(self) -> bool:
        video_ok = False
        design_ok = False

        if self.config.video_path is not None:
            video_ok = os.path.isfile(self.config.video_path)
            if not video_ok:
                log.warning(f"invalid video file: {self.config.video_path}")
        if self.config.design_path is not None:
            design_ok = os.path.isfile(self.config.design_path)
            if not video_ok:
                log.warning(f"invalid design file: {self.config.design_path}")

        return video_ok and design_ok

    def can_filter(self) -> bool:
        return self.transform.is_set

    @api.va.__id__.can_analyze.expose()
    def can_analyze(self) -> bool:
        return self.launched and all([mask.ready or mask.skip for mask in self.masks])

    def _launch(self):
        self.load_config()

        log.debug(f'{self.__class__.__name__}: launch nested instances.')
        self.video = VideoFileHandler(
            self.config.video_path,
            self.config.video
        )
        self.video.set_requested_frames(list(self.frame_numbers()))

        self.design = DesignFileHandler(
            self.config.design_path,
            self.config.design,
            self.config.masks
        )
        self.transform = TransformHandler(
            self.video.shape,
            self.design.shape,
            self.config.transform
        )
        self.masks = self.design.masks
        self.filters = [mask.filter for mask in self.masks]

        # Link self._config to _config of nested instances
        self._gather_config()

        # Initialize FeatureSets
        self._get_featuresets()

    def _get_featuresets(self):
        self._featuresets = {
            feature: FeatureSet(
                tuple(
                    feature.get()(
                        mask,
                        global_config,
                        mask.config.parameters[index] if index < len(mask.config.parameters) else None
                    ) for mask in self.design.masks if not mask.skip
                ),
            ) for index, (feature, global_config) in enumerate(
                zip(
                    self.config.features,
                    self.config.feature_parameters
                )
            )
        }
        self.get_colors()

    def _new_results(self):
        self.results = {}
        for fs, feature in zip(self._featuresets.values(), self.config.features):
            self.results[str(feature)] = pd.DataFrame(
                [],
                columns=['time'] + [f.name for f in fs.features],
                index=list(self.frame_numbers())
            )

    @property
    def position(self):
        if hasattr(self, 'video'):
            return self.video.get_seek_position()
        else:
            return -1.0

    def _set_config(self, config: dict):
        # todo: would be better if nested instance config was *referencing* global config
        if 'video' in config and hasattr(self, 'video'):
            self.video._config(**config.pop('video'))
        if 'design' in config and hasattr(self, 'design'):
            self.design._config(**config.pop('design'))
        if 'transform' in config and hasattr(self, 'transform'):
            self.transform._config(**config.pop('transform'))
        if 'masks' in config and hasattr(self, 'masks'):
            for mask, mask_config in zip(self.masks, config.pop('masks')):
                mask._config(**mask_config)
                if 'filter' in mask_config:
                    mask.filter._config(**mask_config['filter'])

        self._config(**config)
        self._gather_config()

    @api.va.__id__.set_config.expose()
    def set_config(self, config: dict, silent: bool = False) -> dict:
        with self.lock():
            if True:  # todo: sanity check
                do_commit = False
                do_relaunch = False
                log.debug(f"Setting VideoAnalyzerConfig to {config}")

                previous_name = copy.copy(self.config.name)
                previous_desc = copy.copy(self.config.description)
                previous_Nf = copy.copy(self.config.Nf)
                previous_dt = copy.copy(self.config.dt)
                previous_fis = copy.copy(self.config.frame_interval_setting)
                previous_features = copy.deepcopy(self.config.features)  # todo: clean up
                previous_video_path = copy.deepcopy(self.config.video_path)
                previous_design_path = copy.deepcopy(self.config.design_path)
                previous_design = copy.deepcopy(self.config.design)
                previous_flip = copy.deepcopy(self.config.transform.flip)
                previous_turn = copy.deepcopy(self.config.transform.turn)
                previous_roi = copy.deepcopy(self.config.transform.roi)
                previous_masks = copy.deepcopy(self.config.masks)

                # Set implementations
                if hasattr(self, 'transform') and 'transform' in config and 'type' in config['transform']:
                    self.transform.set_implementation(config['transform']['type'])   # todo: shouldn't do this every time
                if hasattr(self, 'design') and 'masks' in config:
                    for i, mask in enumerate(self.design.masks):
                        if 'filter' in config['masks'][i] and 'type' in config['masks'][i]['filter']:
                            mask.filter.set_implementation(config['masks'][i]['filter']['type'])  # todo: shouldn't do this every time

                self._set_config(config)

                if hasattr(self, 'transform'):
                    self.transform._config(**self.config.transform.to_dict())
                    self.transform.set_implementation()   # todo: shouldn't do this every time
                if hasattr(self, 'design'):
                    self.design._config(**self.config.design.to_dict())

                # Check for file changes
                if self.launched and previous_video_path != self.config.video_path:
                    do_commit = True
                    do_relaunch = True

                if self.launched and previous_design_path != self.config.design_path:
                    do_commit = True
                    do_relaunch = True

                # Check for design render changes
                if previous_design != self.config.design:
                    self.design._render(mask_config=self.config.masks)
                    self.transform._design_shape = self.design.shape
                    self.estimate_transform()
                    do_commit = True

                # Check for name/description changes
                if self.config.name != previous_name:
                    do_commit = True
                if self.config.description != previous_desc:
                    do_commit = True

                # Check for changes in frames
                if hasattr(self, 'video'):
                    if any([
                        previous_Nf != self.config.Nf,
                        previous_dt != self.config.dt,
                        previous_fis != self.config.frame_interval_setting
                    ]):
                        self.video.set_requested_frames(list(self.frame_numbers()))
                        do_commit = True

                # Check for changes in features
                if previous_features != self.config.features:
                    if self.launched:
                        self._get_featuresets()

                    do_commit = True

                # Get featureset instances  todo: overlap with previous block?
                if self.launched and not self._featuresets:
                    self._get_featuresets()

                # Check for ROI adjustments
                if previous_flip != self.config.transform.flip \
                        or previous_turn != self.config.transform.turn \
                        or previous_roi != self.config.transform.roi:
                    self.estimate_transform()  # todo: self.config.bla.thing should be exactly self.bla.config.thing always
                    do_commit = True

                # Check for mask adjustments
                if previous_masks != self.config.masks:
                    for i, mask in enumerate(self.design.masks):
                        mask.set_config(self.config.masks[i].to_dict())

                    do_commit = True

                if do_commit and not silent:  # todo: better config handling in AnalysisMdoel.store() instead!
                    self.commit()

                if do_relaunch:
                    self._launch()

                # Check for state transitions
                self.state_transition(push=True)

                config = self.get_config()

                # Push config event
                self.event(PushEvent.CONFIG, config)

                # Push streams
                streams.update()

                return config


    @stream
    @api.va.__id__.get_frame.expose()
    def get_transformed_frame(self, frame_number: Optional[int] = None) -> np.ndarray:
        """Get a video frame transformed to design-space

        :attr:`shapeflow.api._VideoAnalyzerDispatcher.get_transformed_frame`

        Can be streamed to the user interface.

        Parameters
        ----------
        frame_number: Optional[int]
            The frame number to get. If ``None``, get the current frame number.

        Returns
        -------
        np.ndarray
            An image (design-space)
        """
        return self.transform(self.read_frame(frame_number))

    @stream
    @api.va.__id__.get_inverse_transformed_overlay.expose()
    def get_inverse_transformed_overlay(self) -> np.ndarray:
        """Get the design overlay image transformed to video-space

        :attr:`shapeflow.api._VideoAnalyzerDispatcher.get_inverse_transformed_overlay`

        Can be streamed tothe user interface.

        Returns
        -------
        np.ndarray
            An image (in video-space)
        """
        return self.transform.inverse(self.design._overlay)

    @api.va.__id__.get_colors.expose()  # todo: per feature in each feature set; maybe better as a dict instead of a list of tuples?
    def get_colors(self) -> Tuple[str, ...]:
        """Get the list of colors to use for each mask

        :attr:`shapeflow.api._VideoAnalyzerDispatcher.get_colors`

        Returns
        -------
        Tuple[str, ...]
            A tuple of CSS-compatible hex RGB strings
        """
        if len(self.config.features) == 0:
            return tuple([])
        return tuple([css_hex(c) for c in self._featuresets[self.config.features[0]].resolve_colors()]) # todo: assuming that number of masks doesn't change per featureset

    def frame_numbers(self) -> Generator[int, None, None]:
        """Get the requested frame numbers

        Returns
        -------
        Generator[int, None, None]
            An iterator that returns the requested frame numbers
        """
        if self.config.frame_interval_setting == FrameIntervalSetting('Nf'):
            return frame_number_iterator(self.video.frame_count-1, Nf = self.config.Nf)
        elif self.config.frame_interval_setting == FrameIntervalSetting('dt'):
            return frame_number_iterator(self.video.frame_count-1, dt = self.config.dt, fps = self.video.fps)
        else:
            raise NotImplementedError(self.config.frame_interval_setting)

    @stream
    @api.va.__id__.get_inverse_overlaid_frame.expose()
    def get_inverse_overlaid_frame(self, frame_number: Optional[int] = None) -> np.ndarray:
        """Get a raw video frame overlaid with the inverse transformed design
        overlay. Used to evaluate video-design alignment.

        :attr:`shapeflow.api._VideoAnalyzerDispatcher.get_inverse_overlaid_frame`

        Can be streamed tothe user interface.

        Parameters
        ----------
        frame_number: Optional[int]
            The frame number to get. If ``None``, get the current frame number.

        Returns
        -------
        np.ndarray
            An image (video-space)
        """
        if self.transform.is_set:
            return cv2.cvtColor(  # todo: loads of unnecessary color conversion here
                overlay(
                    cv2.cvtColor(self.read_frame(frame_number), cv2.COLOR_HSV2BGR),
                    self.transform.inverse(self.design._overlay), # type: ignore
                    alpha=self.design.config.overlay_alpha
                ), cv2.COLOR_BGR2HSV)
        else:
            log.debug('transform not set, showing raw frame')
            return self.read_frame(frame_number)

    @api.va.__id__.seek.expose()
    def seek(self, position: Optional[float] = None) -> float:
        """Seek the video to a relative position

        :attr:`shapeflow.api._VideoAnalyzerDispatcher.seek`

        Parameters
        ----------
        position: float
            A relative position in the video, with 0 the start and 1 the end.

        Returns
        -------
        float
            The resulting relative position. This may differ from the original
            requested position due to being resolved to the nearest requested
            frame number.
            This improves performance if cached frames can be reused.
        """
        self.video.seek(position)
        self.push_status()

        return self.position

    @api.va.__id__.estimate_transform.expose()
    def estimate_transform(self, roi: Optional[dict] = None) -> Optional[dict]:
        """Estimate the video-design transform from a ROI

        :attr:`shapeflow.api._VideoAnalyzerDispatcher.estimate_transform`

        Parameters
        ----------
        roi: Optional[dict]
            A region of interest as a ``dict``. Must be compatible with
            :class:`shapeflow.maths.coordinates.Roi`. If ``None``, the current
            :attr:`shapeflow.config.TransformHandlerConfig.roi` will be used.

        Returns
        -------
        Optional[dict]
            The region of interest that was provided, or the current region of
            interest if ``None``.
        """
        if roi is None:
            roi_config = self.transform.config.roi
        else:
            roi_config = Roi(**roi)

        self.transform.estimate(roi_config)

        self.state_transition()
        self.event(PushEvent.CONFIG, self.get_config())

        if roi_config is not None:
            return roi_config.dict()
        else:
            return None

    @api.va.__id__.clear_roi.expose()
    def clear_roi(self) -> None:
        """Clear the current region of interest and video-design transform

        :attr:`shapeflow.api._VideoAnalyzerDispatcher.clear_roi`
        """
        self.transform.clear()
        self.state_transition()

    @api.va.__id__.turn_cw.expose()
    def turn_cw(self) -> None:
        """Add a clockwise 90° turn to this analyzer's
        :attr:`shapeflow.config.TransformHandlerConfig.turn`

        :attr:`shapeflow.api._VideoAnalyzerDispatcher.turn_cw`
        """
        self.set_config(
            {'transform': {'turn': self.config.transform.turn + 1}}
        )

    @api.va.__id__.turn_ccw.expose()
    def turn_ccw(self) -> None:
        """Add a counter-clockwise 90° turn to this analyzer's
        :attr:`shapeflow.config.TransformHandlerConfig.turn`

        :attr:`shapeflow.api._VideoAnalyzerDispatcher.turn_ccw`
        """
        self.set_config(
            {'transform': {'turn': self.config.transform.turn - 1}}
        )

    @api.va.__id__.flip_h.expose()
    def flip_h(self) -> None:
        """Toggle this analyzer's
        :attr:`shapeflow.config.TransformHandlerConfig.flip`'s
        :attr:`~shapeflow.config.FlipConfig.horizontal`

        :attr:`shapeflow.api._VideoAnalyzerDispatcher.flip_h`
        """
        self.set_config(
            {'transform': {'flip': {'horizontal': not self.config.transform.flip.horizontal}}}
        )

    @api.va.__id__.flip_v.expose()
    def flip_v(self) -> None:
        """Toggle this analyzer's
        :attr:`shapeflow.config.TransformHandlerConfig.flip`'s
        :attr:`~shapeflow.config.FlipConfig.vertical`

        :attr:`shapeflow.api._VideoAnalyzerDispatcher.flip_v`
        """
        self.set_config(
            {'transform': {'flip': {'vertical': not self.config.transform.flip.vertical}}}
        )

    @api.va.__id__.undo_config.expose()
    def undo_config(self, context: Optional[str] = None) -> dict:  # todo: implement undo/redo context (e.g. transform, masks)
        """Undo this analyzer's last configuration change

        :attr:`shapeflow.api._VideoAnalyzerDispatcher.undo_config`

        Parameters
        ----------
        context: str
            The context in which to undo. If ``context`` is ``None``, the
            previous configuration will be applied. If ``context`` is e.g.
            ``"transform"``, the latest configuration with a
            :attr:`~shapeflow.config.VideoAnalyzerConfig.transform`
            different from the current one will be applied.

        Returns
        -------
        dict
            A configuration ``dict``
        """
        with self.lock():
            undo, id = self.model.get_undo_config(context)
        if undo is not None and id is not None:
            # self.notice(f"undo: grabbed config {id}")
            self.state_transition()
        return self.set_config(undo, silent=(context is None))

    @api.va.__id__.redo_config.expose()
    def redo_config(self, context: Optional[str] = None) -> dict:
        """Redo this analyzer's last undone configuration change

        :attr:`shapeflow.api._VideoAnalyzerDispatcher.redo_config`

        Parameters
        ----------
        context: str
            The context in which to redo. If ``context`` is ``None``, the
            previous configuration will be applied. If ``context`` is e.g.
            ``"transform"``, the latest configuration with a
            :attr:`~shapeflow.config.VideoAnalyzerConfig.transform`
            different from the current one will be applied.

        Returns
        -------
        dict
            A configuration ``dict``
        """

        with self.lock():
            redo, id = self.model.get_redo_config(context)
        if redo is not None and id is not None:
            # self.notice(f"redo: grabbed config {id}")
            self.state_transition()
        return self.set_config(redo, silent=(context is None))

    @api.va.__id__.set_filter_click.expose()
    def set_filter_click(self, relative_x: float, relative_y: float) -> None:
        """Configure a filter by clicking an "in"-pixel on the image

        :attr:`shapeflow.api._VideoAnalyzerDispatcher.set_filter_click`

        Parameters
        ----------
        relative_x: float
            The 'x'-position of an "in"-pixel in relative video-space
        relative_y: float
            The 'y'-position of an "in"-pixel in relative video-space
        """
        log.debug(f'set_filter_click @ ({relative_x}, {relative_y})')

        design_space_click = ShapeCoo(
            x = relative_x,
            y = relative_y,
            shape = self.design.shape[::-1]
        )

        hits = [mask for mask in self.masks if mask.contains(design_space_click)]

        if len(hits) == 1:
            hit = hits[0]
            frame = self.read_frame()
            video_space_click: Optional[ShapeCoo] = self.transform.coordinate(
                design_space_click
            )
            assert video_space_click is not None

            color = HsvColor(*video_space_click.value(frame))
            log.debug(f"color @ {video_space_click.idx}: {color}")

            hit.set_filter(color)

            for fs in self._featuresets.values():
                for feature in fs.features:
                    assert isinstance(feature, MaskFunction)
                    try:
                        if feature.mask == hit:  # type: ignore
                            feature._ready = True
                    except AttributeError:
                        pass

            self.get_colors()

            self.state_transition()
            self.event(PushEvent.CONFIG, self.get_config())
            self.commit()

            streams.update()
            self.commit()
        elif len(hits) == 0:
            log.debug(f"no hit for {design_space_click.idx}")
        elif len(hits) > 1:
            self.notice(
                f"Multiple valid options: {[hit.name for hit in hits]}. "
                f"Select a point where masks don't overlap."
            )

    @api.va.__id__.clear_filters.expose()
    def clear_filters(self) -> bool:
        """Clear this analyzer's filter configuration

        :attr:`shapeflow.api._VideoAnalyzerDispatcher.clear_filters`
        """
        log.debug(f"clearing filters")

        for mask in self.masks:
            mask.clear_filter()

        self.set_state(AnalyzerState.CAN_FILTER)
        self.state_transition()
        self.event(PushEvent.CONFIG, self.get_config())
        self.commit()

        streams.update()

        return True

    @stream
    @api.va.__id__.get_state_frame.expose()
    def get_state_frame(self, frame_number: Optional[int] = None, featureset: Optional[int] = None) -> np.ndarray:
        """Get a state frame. Used to evaluate filter configuration.

        :attr:`shapeflow.api._VideoAnalyzerDispatcher.get_state_frame`

        Can be streamed tothe user interface.

        Parameters
        ----------
        frame_number: Optional[int]
            The frame number to get. If ``None``, get the current frame number.
        featureset: Optional[int]
            The index of the :class:`~shapeflow.core.backend.FeatureSet`
            for which to get the state frame. If ``None``, use 0.
            Feature sets are taken from this analyzer's
            :attr:`~shapeflow.config.VideoAnalyzerConfig.features`.

        Returns
        -------
        np.ndarray
            An image (design-space)
        """
        # todo: eliminate duplicate code ~ calculate (calculate should just call get_state_frame, ideally)

        if featureset is None:
            featureset = 0

        # Empty state image in BGR
        state = np.zeros(self.design._overlay.shape, dtype=np.uint8)

        if hasattr(self, '_featuresets') and len(self._featuresets):
            frame = self.transform(self.read_frame(frame_number))
            assert frame is not None

            k,fs = list(self._featuresets.items())[featureset]

            for feature in fs._features:
                if not feature.skip:
                    state = feature.state(
                        frame.copy(),       # don't overwrite self.frame ~ cv2 dst parameter
                        state               # additive; each feature adds to state
                    )

            # Add overlay on top of state
            # state = overlay(self.design._overlay.copy(), state, self.design.config.overlay_alpha)
        else:
            log.debug('skipping state frame')

        state[np.equal(state, 0)] = 255
        return cv2.cvtColor(state, cv2.COLOR_BGR2HSV)

    @api.va.__id__.get_overlay_png.expose()
    def get_overlay_png(self) -> bytes:
        """Get this analyzer's design overlay

        :attr:`shapeflow.api._VideoAnalyzerDispatcher.get_overlay_png`

        Returns
        -------
        bytes
            The design overlay encoded as PNG
        """
        _, buffer = cv2.imencode('.png', self.design._overlay.copy())
        return buffer.tobytes()

    def get_mask_rects(self) -> Dict[str, np.ndarray]:
        # todo: placeholder -- mask rect info to frontend (in relative coordinates)
        return {mask.name: mask.rect for mask in self.masks}

    def calculate(self, frame_number: int) -> None:
        """Calculate this analyzer's
        :attr:`~shapeflow.config.VideoAnalyzerConfig.features` for a frame.

        Parameters
        ----------
        frame_number: int
            The frame to calculate for

        Returns
        -------
        None
            Results are stored in :attr:`~shapeflow.video.VideoAnalyzer.results`
        """
        log.debug(f"calculating features for frame {frame_number}")

        try:
            t = self.video.get_time(frame_number)
            raw_frame = self.read_frame(frame_number)

            if raw_frame is not None:
                frame = self.transform(raw_frame)
                assert frame is not None

                for k,fs in self._featuresets.items():
                    values, _ = fs.calculate(frame, state=None)
                    self.results[k].loc[frame_number] = [t] + values
            else:
                self.notice(f"skipping unreadable frame {frame_number}")

        except cv2.error as e:
            log.error(str(e))
            self._error.set()

    @api.va.__id__.analyze.expose()
    def analyze(self) -> bool:
        """Run the configured analysis

        :attr:`shapeflow.api._VideoAnalyzerDispatcher.analyze`

        Returns
        -------
        bool
            Whether the analysis was successful
        """
        if not self.can_analyze():
            return False

        with self.busy_context(AnalyzerState.ANALYZING, AnalyzerState.DONE):
            assert isinstance(self._cancel, threading.Event)

            if self.model is None:
                self.notice(f"{self} has no database model; result data may be lost")

            with self.lock(), self.time(f"Analyzing '{self.id}'"):
                self._new_run()
                self._get_featuresets()
                self.commit()
                self._new_results()

                for fn in self.frame_numbers():
                    if not self.canceled and not self.errored:
                        self.calculate(fn)
                        self.set_progress((fn+1) / self.video.frame_count)
                    else:
                        break

            self.commit()
            if self.model is not None:
                self.model.export_result(manual=False)
            self._new_results()

        if self.canceled:
            self.notice(f"analysis canceled.")
            self.clear_cancel()
            self.set_state(AnalyzerState.CANCELED)
            return False

        if self.errored:
            self.notice(f"analysis aborted due to error.")
            self.clear_error()
            self.set_state(AnalyzerState.ERROR)
            return False

        return True

    def load_config(self) -> None:
        """Load a configuration from the database
        """
        if self._model is not None:
            log.debug('loading config from database...')
            include = ['video', 'design', 'transform', 'masks']

            config = self.model.load_config(
                include=include
            )
            if config is not None:
                self._set_config(config)
                self.commit()

                log.info(f'config ~ database: {config}')
                log.info(f'loaded as {self.config}')
            else:
                log.warning('could not load config')


    @property  # todo: this was deprecated, right?
    def _video_to_hash(self):
        return self.config.video_path

    @property
    def _design_to_hash(self):
        return self.config.design_path

    @api.va.__id__.get_time.expose()
    def get_time(self, frame_number: Optional[int] = None) -> float:
        """Get the time corresponding to a video frame number

        :attr:`shapeflow.api._VideoAnalyzerDispatcher.get_time`

        Parameters
        ----------
        frame_number: Optional[int]
            A frame number. If ``None``, use the current frame number.

        Returns
        -------
        float
            A time in seconds
        """
        return self.video.get_time(frame_number)

    @api.va.__id__.get_fps.expose()
    def get_fps(self) -> float:
        """Get the framerate of the video

        :attr:`shapeflow.api._VideoAnalyzerDispatcher.get_fps`
        """
        return self.video.get_fps()

    @api.va.__id__.get_total_time.expose()
    def get_total_time(self) -> float:
        """Get the total time of the video in seconds

        :attr:`shapeflow.api._VideoAnalyzerDispatcher.get_total_time`
        """
        return self.video.get_total_time()

    @stream
    @api.va.__id__.get_raw_frame.expose()
    def read_frame(self, frame_number: Optional[int] = None) -> np.ndarray:
        """Get a raw video frame.

        :attr:`shapeflow.api._VideoAnalyzerDispatcher.get_raw_frame`

        Can be streamed tothe user interface.

        Parameters
        ----------
        frame_number: Optional[int]
            The frame number to get. If ``None``, get the current frame number.

        Returns
        -------
        np.ndarray
            An image (video-space)
        """
        return self.video.read_frame(frame_number)

    @api.va.__id__.get_seek_position.expose()
    def get_seek_position(self) -> float:
        """Get the current relative seek position in the video

        :attr:`shapeflow.api._VideoAnalyzerDispatcher.get_seek_posititon`
        """
        return self.video.get_seek_position()

    @api.va.__id__.get_relative_roi.expose()
    def get_relative_roi(self) -> dict:
        """Get the current region of interest in relative video-space

        :attr:`shapeflow.api._VideoAnalyzerDispatcher.get_relative_roi`
        """
        return self.transform.get_relative_roi()

    @api.va.__id__.get_coordinates.expose()  # todo: difference with get_relative_roi?
    def get_coordinates(self) -> Optional[list]:
        """Get the current coordinates

        :attr:`shapeflow.api._VideoAnalyzerDispatcher.get_coordinates`
        """
        return self.transform.get_coordinates()


def init(config: BaseAnalyzerConfig) -> BaseAnalyzer:
    mapping: Dict[Type[BaseAnalyzerConfig], Type[BaseAnalyzer]] = {
        VideoAnalyzerConfig: VideoAnalyzer
    }

    return mapping[type(config)](config)
