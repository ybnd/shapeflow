import os
import re
import threading
import copy
from typing import Callable, Any, Dict, Generator, Optional, List, Tuple, Type

import cv2
import numpy as np
import pandas as pd
from OnionSVG import OnionSVG, check_svg

from isimple import get_logger, settings
from isimple.config import VideoFileHandlerConfig, TransformHandlerConfig, \
    HsvRangeFilterConfig, FilterHandlerConfig, MaskConfig, \
    DesignFileHandlerConfig, VideoAnalyzerConfig, load, dump, \
    FrameIntervalSetting, BaseAnalyzerConfig
from isimple.core import RootInstance
from isimple.core.backend import BackendInstance, CachingBackendInstance, \
    Handler, BaseVideoAnalyzer, BackendSetupError, AnalyzerType, Feature, \
    FeatureSet, \
    FeatureType, backend, AnalyzerState
from isimple.core.config import extend, __meta_ext__
from isimple.core.interface import TransformInterface, FilterConfig, \
    FilterInterface, FilterType, TransformType
from isimple.core.streaming import stream, streams
from isimple.endpoints import BackendRegistry
from isimple.maths.colors import HsvColor, BgrColor, convert
from isimple.maths.images import to_mask, crop_mask, area_pixelsum, ckernel, \
    overlay, rect_contains
from isimple.maths.coordinates import Coo
from isimple.util import frame_number_iterator

log = get_logger(__name__)


class VideoFileTypeError(BackendSetupError):
    msg = 'Unrecognized video file type'  # todo: formatting


class VideoFileHandler(CachingBackendInstance):
    """Interface to video files ~ OpenCV
    """
    path: str

    frame_count: int
    fps: float
    frame_number: int
    _requested_frames: List[int]

    _capture: cv2.VideoCapture

    _shape: tuple

    colorspace: str

    _config: VideoFileHandlerConfig
    _class = VideoFileHandlerConfig()

    def __init__(self, video_path, stream_methods: list = None, config: VideoFileHandlerConfig = None):
        super(VideoFileHandler, self).__init__(config)
        self._is_caching = False

        if stream_methods == None:
            stream_methods = [self.read_frame]
        else:
            assert isinstance(stream_methods, list)
            self._stream_methods = stream_methods

        if not os.path.isfile(video_path):
            raise FileNotFoundError

        self.path = video_path
        self._cache = None
        self._background = None

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

    def set_requested_frames(self, requested_frames: List[int]) -> None:
        """Add a list of requested frames.
            Used to determine which frames to cache in the background and
            in `_resolve_frame`
        """
        log.debug(f"Requested frames: {requested_frames}")
        self._requested_frames = requested_frames

        self._touch_keys(
            [self._get_key(self._read_frame, self.path, fn)
             for fn in requested_frames]
        )

    def _cache_frames(self):
        with self.caching():
            self._is_caching = True
            for frame_number in self._requested_frames:
                if self._cancel_caching.is_set():
                    break
                args = (self._read_frame, self.path, frame_number)
                if not self._is_cached(*args):
                    self._cached_call(*args)
            self._is_caching = False
        self.seek(0.5)

    def cache_frames(self):
        if self.config.do_cache and self.config.do_background:
            self._cancel_caching = threading.Event()
            self._background = threading.Thread(target=self._cache_frames)
            self._background.start()

    def _resolve_frame(self, frame_number) -> int:
        """Resolve a frame_number to the nearest requested frame number.
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

    def _read_frame(self, _: str, frame_number: int = None) -> np.ndarray:
        """Read frame from video file, HSV color space
            the `_` parameter is a placeholder for the (unused) path of the
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

    @backend.expose(backend.get_time)
    def get_time(self, frame_number: int = None) -> float:
        if frame_number is None:
            frame_number = self.frame_number

        return self._resolve_frame(frame_number) / self.fps

    @backend.expose(backend.get_fps)
    def get_fps(self) -> float:
        return self.fps

    @stream
    @backend.expose(backend.get_raw_frame)
    def read_frame(self, frame_number: Optional[int] = None) -> np.ndarray:
        """Wrapper for `_read_frame`.
            Enables caching (if in a caching context!) and provides the video
            file's path to determine the cache key.
        """
        if frame_number is None:
            frame_number = self.frame_number

        if settings.cache.resolve_frame_number:
            return self._cached_call(self._read_frame, self.path, self._resolve_frame(frame_number))
        else:
            return self._cached_call(self._read_frame, self.path, frame_number)

    @backend.expose(backend.seek)
    def seek(self, position: float = None) -> float:
        """Seek to the relative position ~ [0,1]
        """
        with self.lock():
            if position is not None:
                frame_number = int(position * self.frame_count)
                if settings.cache.resolve_frame_number:
                    self.frame_number = self._resolve_frame(frame_number)
                else:
                    self.frame_number = frame_number

            log.debug(f"seeking  {self.path} {self.frame_number}/{self.frame_count}")
            streams.update()

            return self.frame_number / self.frame_count

    @backend.expose(backend.get_seek_position)
    def get_seek_position(self) -> float:
        """Get current relative position ~ [0,1]
        """
        return self.frame_number / self.frame_count


@extend(TransformType)
class PerspectiveTransform(TransformInterface):
    def validate(self, transform: np.ndarray) -> bool:
        return transform.shape == (3, 3)

    def from_coordinates(self, roi: dict) -> np.ndarray:
        return np.float32(
            [[roi[corner]['x'], roi[corner]['y']]
             for corner in ['BL', 'TL', 'TR', 'BR']]
        )

    def to_coordinates(self, shape: tuple) -> np.ndarray:
        return np.float32(
                np.array(  # selection rectangle: bottom left to top right
                    [
                        [0, shape[1]],          # BL: (x,y)
                        [0, 0],                 # TL
                        [shape[0], 0],          # TR
                        [shape[0], shape[1]],   # BR
                    ]
                )
            )

    def estimate(self, roi: dict, shape: tuple) -> dict:
        log.vdebug(f'Estimating transform ~ coordinates {roi} & shape {shape}')

        return cv2.getPerspectiveTransform(
            self.from_coordinates(roi),
            self.to_coordinates(shape)
        )

    def transform(self, img: np.ndarray, transform: np.ndarray, shape: tuple) -> np.ndarray:
        return cv2.warpPerspective(
            img, transform, shape,   # can't set destination image here! it's the wrong shape!
            borderValue=(255,255,255),  # makes the border white instead of black ~https://stackoverflow.com/questions/30227979/
        )

    def coordinate(self, coordinate: Coo, transform: np.ndarray, shape: Tuple[int, int]) -> Coo:
        coordinate.transform(transform, shape)
        return coordinate


class TransformHandler(BackendInstance, Handler):
    """Handles coordinate transforms.
    """
    _video_shape: Tuple[int, int]
    _design_shape: Tuple[int, int]
    _inverse: Optional[np.ndarray]

    _stream_methods: list

    _implementation: TransformInterface
    _implementation_factory = TransformType
    _implementation_class = TransformInterface

    _config: TransformHandlerConfig
    _class = TransformHandlerConfig()

    def __init__(self, video_shape, design_shape, stream_methods, config: TransformHandlerConfig):
        super(TransformHandler, self).__init__(config)
        self.set_implementation(self.config.type.__str__())
        self._video_shape = (video_shape[0], video_shape[1])  # Don't include color dimension
        self._design_shape = (design_shape[0], design_shape[1])
        self._stream_methods = stream_methods # type: ignore

        self.set(self.config.matrix)

    @property
    def config(self) -> TransformHandlerConfig:
        return self._config

    @backend.expose(backend.set_transform_implementation)
    def set_implementation(self, implementation: str) -> str:
        # If there's ever any method to set additional transform options, this method/endpoint can be merged into that
        return super(TransformHandler, self).set_implementation(implementation)

    def set(self, transform: Optional[np.ndarray]):
        """Set the transform matrix
        """
        if transform is not None:
            if self._implementation.validate(transform):
                self.config(matrix=transform)
                self._inverse = np.linalg.inv(transform)
            else:
                raise ValueError(f"Invalid transform {transform} for "
                                 f"'{self._implementation.__class__.__name__}'")
        else:
            self.config(matrix=None)
            self._inverse = None

    @backend.expose(backend.get_relative_roi)
    def get_relative_roi(self) -> dict:
        if self.config.roi is not None:
            try:
                return {
                    k: {
                        'x': v['x'],
                        'y': v['y']
                    } for k,v in self.config.roi.items()
                }
            except KeyError:
                return {}
        else:
            return {}

    @backend.expose(backend.estimate_transform)
    def estimate(self, roi: dict) -> None:
        """Estimate the transform matrix from a set of coordinates.
            Coordinates should correspond to the corners of the outline of
            the design, relative to the video frame size:
                x in [0,1] ~ width
                y in [0,1] ~ height
        """
        # todo: sanity check roi

        self.config(roi=roi)

        roi = {
            k: {
            'x': v['x'] * self._video_shape[0],
            'y': v['y'] * self._video_shape[1]
            } for k,v in roi.items()
        }

        self.set(self._implementation.estimate(self.flip(roi), self._design_shape))
        streams.update()

    def flip(self, roi: dict) -> dict:
        if self.config.flip == (True, False):
            # Flip vertically
            return {
                'BL': roi['TL'],
                'TL': roi['BL'],
                'BR': roi['TR'],
                'TR': roi['BR']
            }
        elif self.config.flip == (False, True):
            # Flip horizontally
            return {
                'BL': roi['BR'],
                'TL': roi['TR'],
                'BR': roi['BL'],
                'TR': roi['TL']
            }
        elif self.config.flip == (True, True):
            # Flip both (180° rotation)
            return {
                'BL': roi['TR'],
                'TL': roi['BR'],
                'BR': roi['TL'],
                'TR': roi['BL']
            }
        else:
            return roi

    @backend.expose(backend.clear_roi)
    def clear(self) -> None:
        self.config(roi=None)
        self.config(matrix=None)
        self._inverse = None

        streams.update()

    @backend.expose(backend.get_coordinates)
    def get_coordinates(self) -> Optional[list]:
        if isinstance(self.config.roi, list):
            return self.config.roi
        else:
            return None

    @backend.expose(backend.transform)
    def __call__(self, img: np.ndarray) -> np.ndarray:
        """Transform a frame.
            Writes to the provided variable!
            If caller needs the original value, they should copy explicitly
        """
        if self.config.matrix is not None:
            return self._implementation.transform(img, self.config.matrix, self._design_shape)
        else:
            raise ValueError('transform matrix is not set')
    def coordinate(self, coordinate: Coo) -> Coo:
        """Transform a design coordinate to a video coordinate
        """
        if self._inverse is not None:
            og_co = coordinate.copy()
            co = self._implementation.coordinate(coordinate, self._inverse, self._video_shape[::-1])  # todo: ugh
            return co
        else:
            raise ValueError('inverse transform matrix is not set')

    def inverse(self, img: np.ndarray) -> np.ndarray:
        if self._inverse is not None:
            return self._implementation.transform(img, self._inverse, self._video_shape)
        else:
            raise ValueError('inverse transform matrix is not set')

    @property
    def matrix(self):
        return self.config.matrix


@extend(FilterType)
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
        c0 = np.array(filter.c0)
        c1 = np.array(filter.c1)
        return HsvColor(float(np.mean([c0[0], c1[0]])), 255.0, 200.0)

    def filter(self, img: np.ndarray, filter: HsvRangeFilterConfig) -> np.ndarray:
        c0 = np.array(filter.c0)
        c1 = np.array(filter.c1)
        return cv2.inRange(
            img, np.float32(c0), np.float32(c1), img
        )


class FilterHandler(BackendInstance, Handler):
    _implementation: FilterInterface
    _implementation_factory = FilterType
    _implementation_class = FilterInterface

    _config: FilterHandlerConfig

    def __init__(self, config: FilterHandlerConfig = None):
        super(FilterHandler, self).__init__(config)
        self.set_implementation(self.config.type.__str__())
        if self.config.data is None:
            self.config(data=self._implementation._config_class())

    @property
    def config(self) -> FilterHandlerConfig:
        return self._config

    @backend.expose(backend.get_filter_mean_color)
    def mean_color(self) -> HsvColor:
        return self._implementation.mean_color(self.config.data)

    def set(self, filter: FilterConfig = None, color: HsvColor = None) -> FilterConfig:
        if isinstance(self.config.data, dict):
            self.config.data = FilterConfig(**self.config.data)

        if filter is None:
            if hasattr(self.config.data, 'filter'):
                filter = self._implementation._config_class(**self.config.data.filter)
            else:
                filter = self._implementation._config_class()
        if color is None:
            if hasattr(self.config.data, 'color'):
                color = self.config.data.color
            else:
                color = HsvColor(0,0,0)

        assert isinstance(color, HsvColor)
        self.config(data=self._implementation.set_filter(filter,color))

        log.debug(f"Filter config: {self.config}")

        assert isinstance(self.config.data, FilterConfig)
        return self.config.data

    def set_implementation(self, implementation: str) -> str:
        return super(FilterHandler, self).set_implementation(implementation)

    @backend.expose(backend.filter)
    def __call__(self, frame: np.ndarray) -> np.ndarray:
        assert isinstance(self.config.data, FilterConfig)
        return self._implementation.filter(frame, self.config.data)



class Mask(BackendInstance):
    """Handles masks in the context of a video file
    """

    filter: FilterHandler

    _config: MaskConfig
    _dpi: float

    _part: np.ndarray
    _rect: np.ndarray

    def __init__(
            self,
            mask: np.ndarray,
            name: str,
            config: MaskConfig = None,
            filter: FilterHandler = None,
            dpi: float = None
    ):
        if config is None:
            config = MaskConfig()

        super(Mask, self).__init__(config)
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

        if dpi is None:
            raise BackendSetupError(f'Mask {self.config.name} has no defined DPI.')
        else:
            self._dpi = dpi

    @property
    def config(self) -> MaskConfig:
        return self._config

    def set_filter(self, color: HsvColor) -> FilterConfig:
        filter_config = self.filter.set(color=color)
        self._config.ready = True
        return filter_config

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

    def contains(self, coordinate: Coo) -> bool:
        if rect_contains(self.rect, coordinate):
            return bool(
                self.part[coordinate.idx[0] - self.rect[0], coordinate.idx[1] - self.rect[2]]
            )
        else:
            return False

    @property
    def rows(self):
        return slice(self._rect[0], self._rect[1])

    @property
    def cols(self):
        return slice(self._rect[2], self._rect[3])

    @property
    def name(self):
        return self.config.name

    @property
    def dpi(self):
        return self._dpi

    @property
    def part(self):
        return self._part

    @property
    def rect(self):
        return self._rect


class DesignFileHandler(CachingBackendInstance):
    _overlay: np.ndarray
    _masks: List[Mask]

    _config: DesignFileHandlerConfig
    _class = DesignFileHandlerConfig()

    def __init__(self, path: str, config: DesignFileHandlerConfig = None, mask_config: Tuple[MaskConfig,...] = None):
        super(DesignFileHandler, self).__init__(config)
        if not os.path.isfile(path):
            raise FileNotFoundError

        self._path = path
        with self.caching():
            self._overlay = self.peel_design(path)
            self._shape = (self._overlay.shape[1], self._overlay.shape[0])

            self._masks = []
            for i, (mask, name) in enumerate(zip(*self.read_masks(path))):
                if mask_config is not None and len(mask_config) > 0 and len(mask_config) >= i + 1:  # handle case len(mask_config) < len(self.read_masks(path))
                    self._masks.append(
                        Mask(mask, name, mask_config[i], dpi=self.config.dpi)
                    )
                else:
                    self._masks.append(Mask(mask, name, dpi=self.config.dpi))


    @property
    def config(self) -> DesignFileHandlerConfig:
        return self._config

    def _clear_renders(self):
        log.debug(f'Clearing render directory {settings.render.dir}')
        renders = [f for f in os.listdir(settings.render.dir)]
        for f in renders:
            os.remove(os.path.join(settings.render.dir, f))

    def _peel_design(self, design_path) -> np.ndarray:
        if not os.path.isdir(settings.render.dir):
            os.mkdir(settings.render.dir)
        else:
            self._clear_renders()

        check_svg(design_path)
        OnionSVG(design_path, dpi=self.config.dpi).peel(
            'all', to=settings.render.dir  # todo: should maybe prepend file name to avoid overwriting previous renders?
        )
        print("\n")

        overlay = cv2.imread(
            os.path.join(settings.render.dir, 'overlay.png')
        )

        return overlay

    def _read_masks(self, _) -> Tuple[List[np.ndarray], List[str]]:
        files = os.listdir(settings.render.dir)
        files.remove('overlay.png')

        # Catch file names of numbered layers
        pattern = re.compile('(\d+)[?\-=_#/\\\ ]+([?\w\-=_#/\\\ ]+)')

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

    def peel_design(self, design_path) -> np.ndarray:
        return self._cached_call(self._peel_design, design_path)

    def read_masks(self, design_path) -> Tuple[List[np.ndarray], List[str]]:
        return self._cached_call(self._read_masks, design_path)

    @property
    def shape(self):
        return self._shape

    @backend.expose(backend.get_dpi)
    def get_dpi(self) -> float:
        return self.config.dpi

    @stream
    @backend.expose(backend.get_overlay)
    def overlay(self) -> np.ndarray:
        return self._overlay

    @backend.expose(backend.get_overlay_png)
    def get_overlay_png(self) -> bytes:
        # OpenCV complains if self.overlay (property) is used

        _overlay = self._overlay.copy()

        # Get position of completely white pixels  todo: might look weird ~filtering
        overlay_white = np.logical_and(
            *[_overlay[:,:,i] for i in range(_overlay.shape[2])]
        )

        # Add an alpha channel
        overlay_alpha = cv2.cvtColor(_overlay, cv2.COLOR_BGR2BGRA)

        # Make white transparent
        overlay_alpha[overlay_white] = [0,0,0,255]

        _, buffer = cv2.imencode('.png', overlay_alpha)
        return buffer.tobytes()

    @backend.expose(backend.overlay_frame)
    def overlay_frame(self, frame: np.ndarray) -> np.ndarray:
        frame = cv2.cvtColor(frame, cv2.COLOR_HSV2BGR)
        frame = overlay(frame, self._overlay, self.config.overlay_alpha)
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


class MaskFunction(Feature):
    mask: Mask
    filter: FilterHandler

    _feature_type: FeatureType

    def __init__(self, mask: Mask):
        self.mask = mask
        self.filter = mask.filter

        super(MaskFunction, self).__init__(
            (self.mask, self.filter)
        )

        self._feature_type = FeatureType(self.__class__.__name__)

        self._skip = mask.config.skip
        self._ready = mask.config.ready

    @property
    def feature_type(self) -> FeatureType:
        return self._feature_type

    def unpack(self) -> tuple:
        """Resolve `self.mask.config.parameters` & `self.default_parameters()`
            to a tuple of values in the order of `self.parameters()`
        """

        if self.feature_type in self.mask.config.parameters:
            pars = []
            for parameter in self.parameters():
                if parameter in self.mask.config.parameters[self.feature_type]:
                    pars.append(
                        self.mask.config.parameters[self.feature_type][parameter]
                    )
                else:
                    pars.append(
                        self.parameter_defaults()[parameter]
                    )
            return tuple(pars)
        else:
            return tuple(
                [self.parameter_defaults()[parameter]
                 for parameter in self.parameters()]
            )

    def px2mm(self, value):
        return value / (self.mask.dpi / 25.4)

    def pxsq2mmsq(self, value):
        return value / (self.mask.dpi / 25.4) ** 2

    def _guideline_color(self) -> HsvColor:
        return self.filter.mean_color()

    def value(self, frame) -> Any:
        return self._function(self.filter(self.mask(frame)))

    def state(self, frame: np.ndarray, state: np.ndarray = None) -> np.ndarray:
        """Generate a state image (BGR)
        """
        if state is not None:
            if not self.skip:
                if self.ready:
                    # Masked & filtered pixels ~ frame
                    binary = self.filter(self.mask(frame))
                    substate = np.multiply(
                        np.ones((binary.shape[0], binary.shape[1], 3),
                                dtype=np.uint8),
                        convert(self.color, BgrColor).np
                        # todo: update to isimple.maths.color
                    )
                    state[self.mask.rows, self.mask.cols, :] \
                        += cv2.bitwise_and(substate, substate, mask=binary)
                else:
                    # Not ready -> highlight feature with a rectangle
                    substate = np.zeros((*self.mask.part.shape, 3), dtype=np.uint8)

                    for i,c in enumerate([0, 0, 255]):  # todo: numpy this
                        substate[0:1, :, i] = c
                        substate[-2:-1, :, i] = c
                        substate[:, 0:1, i] = c
                        substate[:, -2:-1, i] = c

                    state[self.mask.rows, self.mask.cols, :] += substate

                  # todo: overwrites rect with white
                return state

    @property
    def name(self) -> str:
        return self.mask.name

    def _function(self, frame: np.ndarray) -> Any:
        raise NotImplementedError


@extend(FeatureType)
class PixelSum(MaskFunction):
    _description = "Masked & filtered area as number of pixels"

    def _function(self, frame: np.ndarray) -> Any:
        return area_pixelsum(frame)


@extend(FeatureType)
class Volume_uL(MaskFunction):
    _description = "Volume ~ masked & filtered area multiplied by channel height"

    _parameters = ('h',)
    _parameter_defaults = {
        'h': 0.153
    }
    _parameter_descriptions = {
        'h': 'height (mm)'
    }

    def _function(self, frame: np.ndarray) -> Any:
        h, = self.unpack()
        return self.pxsq2mmsq(area_pixelsum(frame)) * h  # todo: better parameter handling for Feature subclasses


@extend(AnalyzerType)
class VideoAnalyzer(BaseVideoAnalyzer):
    """Main video handling class
            * Load frames from video files
            * Load mask files
            * Load/save measurement metadata
    """
    _config: VideoAnalyzerConfig
    _class = VideoAnalyzerConfig('', '')  # todo: why is this again?
    _gui: Optional[RootInstance]
    _endpoints: BackendRegistry = backend

    video: VideoFileHandler
    design: DesignFileHandler
    transform: TransformHandler
    features: Tuple[Feature,...]
    results: dict

    _featuresets: Dict[str, FeatureSet]

    def __init__(self, config: VideoAnalyzerConfig = None, multi: bool = False):
        super().__init__(config)
        self._multi = multi
        self.results: dict = {}
        self._gather_instances()

    @property
    def config(self) -> VideoAnalyzerConfig:
        return self._config

    def can_launch(self) -> bool:  # todo: endpoint?
        if self.config.video_path is not None \
                and self.config.design_path is not None:
            # todo: push get_state streamer
            return os.path.isfile(self.config.video_path) \
                   and os.path.isfile(self.config.design_path)
        else:
            return False

    def can_run(self) -> bool:  # todo: endpoint?
        if self.can_launch():
            # todo: push get_state streamer
            return self.ok_to_run
        else:
            return False

    def _launch(self):
        self.load_config()

        log.debug(f'{self.__class__.__name__}: launch nested instances.')
        self.video = VideoFileHandler(self.config.video_path, self.stream_methods, self.config.video)  # todo: stream_methods list should be generated automatically
        self.video.set_requested_frames(list(self.frame_numbers()))
        self.design = DesignFileHandler(self.config.design_path, self.config.design, self.config.masks)
        self.transform = TransformHandler(self.video.shape, self.design.shape, self.stream_methods, self.config.transform)
        self.masks = self.design.masks
        self.filters = [mask.filter for mask in self.masks]

        # Link self._config to _config of nested instances
        self.config(
            video=self.video.config,
            design=self.design.config,
            transform=self.transform.config,
            masks=tuple([m.config for m in self.masks]),
        )

        # Start caching frames in the background
        self.video.cache_frames()

        # Initialize FeatureSets
        self._get_featuresets()

        # todo: add some stuff to do this automagically
        backend.expose(backend.get_frame)(self.get_transformed_frame)
        backend.expose(backend.get_inverse_overlaid_frame)(self.get_inverse_overlaid_frame)
        backend.expose(backend.get_overlaid_frame)(self.get_frame_overlay)
        backend.expose(backend.get_state_frame)(self.get_state_frame)
        backend.expose(backend.get_colors)(self.get_colors)

        # Commit to history
        self.commit()

        # todo: push get_state streamer

    def _get_featuresets(self):
        features = []
        for feature in self.config.features:
            if isinstance(feature, str):
                features.append(FeatureType(feature))
            elif isinstance(feature, FeatureType):
                features.append(feature)

        self._config.features = tuple(features)

        self._featuresets = {
            str(feature): FeatureSet(
                tuple(feature.get()(mask) for mask in self.design.masks),
            ) for feature in self.config.features
        }
        self._new_results()

    def _new_results(self):
        for fs, feature in zip(self._featuresets.values(), self.config.features):
            self.results[str(feature)] = pd.DataFrame(
                [], columns=['time'] + [f.name for f in fs.features], index=list(self.frame_numbers())
            )

    @backend.expose(backend.get_config)
    def get_config(self) -> dict:
        return self.config.to_dict()

    @backend.expose(backend.set_config)
    def set_config(self, config: dict) -> dict:
        with self.lock():
            if True:  # todo: sanity check
                do_commit = False
                log.debug(f"Setting VideoAnalyzerConfig to {config}")

                previous_features = copy.copy(self.config.features)
                previous_video_path = copy.copy(self.config.video_path)
                previous_design_path = copy.copy(self.config.design_path)
                previous_flip = copy.copy((self.config.transform.flip))

                self._config(**config)
                self._config.resolve()

                if hasattr(self, 'transform'):
                    self.transform._config(**self.config.transform.to_dict())
                if hasattr(self, 'design'):
                    self.design._config(**self.config.design.to_dict())

                # Check for changes in features
                if previous_features != self.config.features:
                    # Add feature parameters to mask config
                    for feature in self.config.features:  # todo: move down to Feature level
                        if isinstance(feature, str):
                            feature = FeatureType(feature)
                        for mask in self.config.masks:


                            f = feature.get()
                            if f not in mask.parameters:
                                mask.parameters.update({
                                    feature: self.config.parameters[feature]
                                })

                    do_commit = True
                    try:
                        log.debug('updating featuresets')
                        self._get_featuresets()
                    except AttributeError:
                        pass

                # Check for flip
                if previous_flip != self.config.transform.flip:
                    self.transform.estimate(self.transform.config.roi)  # todo: self.config.bla.thing should be exactly self.bla.config.thing always
                    do_commit = True

                # Commit to history if files were changed
                if previous_video_path != self.config.video_path or previous_design_path != self.config.design_path:
                    do_commit = True

                if do_commit:
                    self.commit()  # todo: isimple.video doesn't know about isimple.history!

                # Check for state transitions
                if self._state == AnalyzerState.INCOMPLETE:
                    if self.can_launch():
                        self._state = AnalyzerState.CAN_LAUNCH
                if self._state == AnalyzerState.LAUNCHED:
                    if self.can_run():
                        self._state = AnalyzerState.CAN_RUN

                # Push to streams
                streams.update()

                return self.config.to_dict()

    @stream
    @backend.expose(backend.get_frame)  # todo: would like to have some kind of 'deferred expose' decorator?
    def get_transformed_frame(self, frame_number: Optional[int] = None) -> np.ndarray:
        return self.transform(self.video.read_frame(frame_number))

    @backend.expose(backend.get_inverse_transformed_overlay)
    def get_inverse_transformed_overlay(self) -> np.ndarray:
        return self.transform.inverse(self.design._overlay)

    @backend.expose(backend.get_overlaid_frame)
    def get_frame_overlay(self, frame_number: int) -> np.ndarray:
        return self.design.overlay_frame(
            self.get_transformed_frame(frame_number))

    @backend.expose(backend.get_colors)  # todo: per feature in each feature set; maybe better as a dict instead of a list of tuples?
    def get_colors(self) -> List[Tuple[HsvColor, ...]]:
        return [featureset.get_colors() for featureset in self._featuresets.values()]

    def frame_numbers(self) -> Generator[int, None, None]:
        if self.config.frame_interval_setting == FrameIntervalSetting('Nf'):
            return frame_number_iterator(self.video.frame_count-1, Nf = self.config.Nf)
        elif self.config.frame_interval_setting == FrameIntervalSetting('dt'):
            return frame_number_iterator(self.video.frame_count-1, dt = self.config.dt, fps = self.video.fps)
        else:
            raise NotImplementedError(self.config.frame_interval_setting)

    @stream
    @backend.expose(backend.get_inverse_overlaid_frame)
    def get_inverse_overlaid_frame(self, frame_number: Optional[int] = None) -> np.ndarray:
        try:
            return cv2.cvtColor(  # todo: loads of unnecessary color conversion here
                overlay(
                    cv2.cvtColor(self.video.read_frame(frame_number), cv2.COLOR_HSV2BGR),
                    self.transform.inverse(self.design._overlay),
                    alpha=self.design.config.overlay_alpha
                ), cv2.COLOR_BGR2HSV)
        except ValueError:
            log.debug('transform not set, showing raw frame')
            return self.video.read_frame(frame_number)

    @backend.expose(backend.undo_roi)
    def undo_roi(self) -> dict:
        from isimple.history import History
        _history = History()

        self.commit()
        roi = _history.get_roi(self.model, next=False)
        if roi is not None:
            self.transform.estimate(roi)
            return roi
        else:
            return self.transform.config.roi

    @backend.expose(backend.redo_roi)
    def redo_roi(self) -> dict:
        from isimple.history import History
        _history = History()

        self.commit()
        roi = _history.get_roi(self.model, next=True)
        if roi is not None:
            self.transform.estimate(roi)
            return roi
        else:
            return self.transform.config.roi

    @backend.expose(backend.set_filter_click)
    def set_filter_click(self, relative_x: float, relative_y: float) -> dict:
        response = {}

        click = Coo(
            x = relative_x,
            y = relative_y,
            shape = self.design.shape[::-1]  # todo: ugh
        )

        hits = [mask for mask in self.masks if mask.contains(click)]

        if len(hits) == 1:
            hit = hits[0]
            frame = self.video.read_frame()
            click = self.transform.coordinate(click)  # todo: transformation is fucked

            color = HsvColor(*click.value(frame))
            log.debug(f"color @ {click.idx}: {color}")

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

            streams.update()
            self.commit()
        elif len(hits) == 0:
            log.debug(f"no hit for {click.idx}")
        elif len(hits) > 1:
            message = f"Multiple valid options: {[hit.name for hit in hits]}. Select a point where masks don't overlap."
            response['message'] = message
            log.warning(message)
        return response


    @stream
    @backend.expose(backend.get_state_frame)
    def get_state_frame(self, frame_number: Optional[int] = None, featureset: int = 0) -> np.ndarray:
        # todo: eliminate duplicate code ~ calculate (calculate should just call get_state_frame, ideally)

        # Empty state image in BGR
        state = np.zeros(self.design._overlay.shape, dtype=np.uint8)

        if hasattr(self, '_featuresets') and len(self._featuresets):
            frame = self.transform(self.video.read_frame(frame_number))

            k,fs = list(self._featuresets.items())[featureset]

            for feature in fs._features:
                if not feature.skip:
                    value, state = feature.calculate(
                        frame.copy(),       # don't overwrite self.frame ~ cv2 dst parameter
                        state               # additive; each feature adds to state
                    )

            # Add overlay on top of state
            # state = overlay(state, self.design._overlay.copy(), self.design.config.overlay_alpha)
        else:
            log.debug('skipping state frame')

        state[np.equal(state, 0)] = 255
        return cv2.cvtColor(state, cv2.COLOR_BGR2HSV)

    def calculate(self, frame_number: int, update_callback: Callable = None):
        """Return a state image for each FeatureSet
        """
        log.debug(f"Calculating for frame {frame_number}")

        t = self.video.get_time(frame_number)
        raw_frame = self.video.read_frame(frame_number)
        frame = self.transform(raw_frame)

        V = []
        S = []
        for k,fs in self._featuresets.items():  # todo: for each feature set -- export data for a separate legend to add to the state plot
            values = []
            state = np.zeros(frame.shape, dtype=np.uint8)  # BGR state image  # todo: should only generate state images when explicitly requested
            # todo: may be faster / more memory-efficient to keep state[i] and set it to 0

            for feature in fs._features:  # todo: make featureset iterable maybe
                value, state = feature.calculate(
                    frame.copy(),  # don't overwrite self.frame ~ cv2 dst parameter  # todo: better to let OpenCV handle copying, or not?
                    state               # additive; each feature adds to state
                )
                values.append(value)

            state[np.equal(state, 0)] = 255

            # Add overlay on top of state
            state = overlay(state, self.design._overlay, self.design.config.overlay_alpha)

            V.append(values)   # todo: value values value ugh
            S.append(state)

            self.results[k].loc[frame_number] = [t] + values

        # todo: # todo: push get_state streamer
        if update_callback is not None:
            update_callback(
                t,
                V, # todo: this is per feature in each feature set; maybe better as dict instead of list of lists?
                S,     # todo: keep values (in order to save them)
                frame
            )

    def analyze(self) -> bool:
        assert isinstance(self._cancel, threading.Event)
        self._state = AnalyzerState.RUNNING
        # todo: push get_state streamer

        if self.model is None:
            log.warning(f"{self} has no database model; data may be lost")

        with self.lock(), self.time():
            self._get_featuresets()
            self.save_config()

            log.debug(f"Analyzing with features: {[f for f in self._featuresets]}.")

            for fn in self.frame_numbers():
                if self._cancel.is_set():
                    break
                self.calculate(fn) #, update_callback)
                self._progress = fn / self.video.frame_count

            # Save results & configuration to database
            # todo: push get_state streamer
            self.commit()
        if not self._cancel.is_set():
            self._state = AnalyzerState.DONE
            # todo: push get_state streamer
            return True
        else:
            self._cancel.clear()
            # todo: push get_state streamer
            return False

    def load_config(self):  # todo: look in history instead of file next to video
        """Load video analysis configuration from history database
        """
        log.info('loading config from database...')
        include = ['video', 'design', 'transform', 'masks']

        from isimple.history import History, VideoFileModel, DesignFileModel  # todo: fix history / video circular dependency
        _history = History()

        if self.config.video_path is not None and os.path.isfile(self.config.video_path):
            video = _history.add_file(self.config.video_path, VideoFileModel)
            if self.config.design_path is not None and os.path.isfile(self.config.design_path):
                design = _history.add_file(self.config.design_path, DesignFileModel)
                config = _history.get_config(
                    self.model,
                    video,
                    design,
                    include = include
                )
                design.remove()
            else:
                config = _history.get_config(
                    self.model,
                    video,
                    include=include
                )
            video.remove()

            self._config(**config)
            self._config.resolve()

            log.debug(f'loaded config: {config}')
        else:
            log.debug('could not load config - no video path!')
        # todo: push get_state streamer

    def save_config(self, path: str = None):  # todo: in isimple.og, make LegacyVideoAnalyzer(VideoAnalyzer) that implements these
        """Save video analysis configuration
        """
        if path is None and self.config.video_path:
            path = self.config.video_path

        if path is not None:
            path = os.path.splitext(path)[0] + __meta_ext__
            config = self._gather_config()
            dump(config, path)
        else:
            log.warning(f"No path provided to `save_config`; no video file either.")

    def _gather_config(self) -> VideoAnalyzerConfig:
        """Gather configuration from instances  todo: should not be needed since self._config is linked to nested instance _config ~ _launch()
        """
        self.config(video=self.video.config)
        self.config(design=self.design.config)
        self.config(transform=self.transform.config)
        self.config(masks=tuple([m.config for m in self.masks]))
        return self.config

    @property  # todo: this was deprecated, right?
    def _video_to_hash(self):
        return self.config.video_path

    @property
    def _design_to_hash(self):
        return self.config.design_path


def init(config: BaseAnalyzerConfig) -> BaseVideoAnalyzer:
    mapping: Dict[Type[BaseAnalyzerConfig], Type[BaseVideoAnalyzer]] = {
        VideoAnalyzerConfig: VideoAnalyzer
    }

    return mapping[type(config)](config)
