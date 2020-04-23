import os
import re
import threading
import copy
from typing import Callable, Any, Dict, Generator, Optional, List, Tuple

import cv2
import numpy as np
import pandas as pd
from OnionSVG import OnionSVG, check_svg

from isimple import get_logger, settings
from isimple.config import VideoFileHandlerConfig, TransformHandlerConfig, \
    HsvRangeFilterConfig, FilterHandlerConfig, MaskConfig, \
    DesignFileHandlerConfig, VideoAnalyzerConfig, load, dump, \
    FrameIntervalSetting
from isimple.core import RootInstance
from isimple.core.backend import BackendInstance, CachingBackendInstance, \
    Handler, BaseVideoAnalyzer, BackendSetupError, AnalyzerType, Feature, \
    FeatureSet, \
    FeatureType, backend, AnalyzerState
from isimple.core.config import extend, __meta_ext__, Config
from isimple.core.interface import TransformInterface, FilterConfig, \
    FilterInterface, FilterType, TransformType
from isimple.core.streaming import stream, streams
from isimple.endpoints import BackendRegistry
from isimple.endpoints import GuiRegistry as gui
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
    _capture: cv2.VideoCapture

    _shape: tuple
    _stream_methods: list

    _requested_frames: List[int]
    frame_number: int

    colorspace: str

    _config: VideoFileHandlerConfig
    _class = VideoFileHandlerConfig()


    def __init__(self, video_path, stream_methods: list = None, config: VideoFileHandlerConfig = None):
        super(VideoFileHandler, self).__init__(config)
        if stream_methods == None:
            stream_methods = [self.read_frame]
        else:
            assert isinstance(stream_methods, list)
            self._stream_methods = stream_methods

        if not os.path.isfile(video_path):
            raise FileNotFoundError

        self.path = video_path
        self.name = video_path.split('\\')[-1].split('.png')[0]
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

    def _resolve_frame(self, frame_number) -> int:
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

    def _read_frame(self, _: str, frame_number: int = None) -> np.ndarray:
        """Read frame from video file, HSV color space
            the `_` parameter is a placeholder for the (unused) path of the
            video file, which is used to make the cache key in order to make
            this function cachable across multiple files.
        """
        if frame_number is None:
            frame_number = self.frame_number

        self._set_position(frame_number)  # todo: check if it's a problem for multiple cv2.VideoCapture instances to read from the same file at the same time (case of background caching while seeking in the video)
        ret, frame = self._capture.read()

        if ret:
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV, frame)
            return frame

    @backend.expose(backend.get_total_frames)
    def get_total_frames(self) -> int:
        return self.frame_count

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

        if self.config.do_resolve_frame_number:
            return self._cached_call(self._read_frame, self.path, self._resolve_frame(frame_number))
        else:
            return self._cached_call(self._read_frame, self.path, frame_number)

    @backend.expose(backend.seek)
    def seek(self, position: float = None) -> float:
        """Seek to the relative position ~ [0,1]
        """
        if position is not None:
            frame_number = int(position * self.frame_count)
            if self.config.do_resolve_frame_number:
                self.frame_number = self._resolve_frame(frame_number)
            else:
                self.frame_number = frame_number

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

    def estimate(self, roi: dict, shape: tuple) -> dict:
        log.vdebug(f'Estimating transform ~ coordinates {roi} & shape {shape}')

        roi_video = np.float32(
                [[roi[corner]['x'], roi[corner]['y']]
                 for corner in ['BL', 'TL', 'TR', 'BR']]
            )
        roi_design = np.float32(
                np.array(  # selection rectangle: bottom left to top right
                    [
                        [0, shape[1]],          # BL: (x,y)
                        [0, 0],                 # TL
                        [shape[0], 0],          # TR
                        [shape[0], shape[1]],   # BR
                    ]
                )
            )
        return cv2.getPerspectiveTransform(roi_video, roi_design)

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
    _inverse: np.ndarray

    _stream_methods: list

    _implementation: TransformInterface
    _implementation_factory = TransformType
    _implementation_class = TransformInterface

    _config: TransformHandlerConfig
    _class = TransformHandlerConfig()

    def __init__(self, video_shape, design_shape, stream_methods, config: TransformHandlerConfig):
        super(TransformHandler, self).__init__(config)
        self.set_implementation(self.config.type)
        self._video_shape = (video_shape[0], video_shape[1])  # Don't include color dimension
        self._design_shape = (design_shape[0], design_shape[1])
        self._stream_methods = stream_methods # type: ignore

        self._inverse = np.linalg.inv(self.config.matrix)

    @property
    def config(self) -> TransformHandlerConfig:
        return self._config

    @backend.expose(backend.set_transform_implementation)
    def set_implementation(self, implementation: str) -> str:
        # If there's ever any method to set additional transform options, this method/endpoint can be merged into that
        return super(TransformHandler, self).set_implementation(implementation)

    def set(self, transform: np.ndarray):
        """Set the transform matrix
        """
        if self._implementation.validate(transform):
            self.config(matrix=transform)
            self._inverse = np.linalg.inv(transform)
        else:
            raise ValueError(f"Invalid transform {transform} for "
                             f"'{self._implementation.__class__.__name__}'")

    @backend.expose(backend.get_relative_roi)
    def get_relative_roi(self) -> dict:
        if self.config.roi['BR']['x'] > 1:  # todo: temporary, handle accidental absolute roi more elegantly
            return {
                k: {
                    'x': v['x'] / self._video_shape[0],
                    'y': v['y'] / self._video_shape[1]
                } for k,v in self.config.roi.items()
            }
        else:
            return self.config.roi

    @backend.expose(backend.estimate_transform)
    def estimate(self, roi: dict) -> bool:
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

        self.set(self._implementation.estimate(roi, self._design_shape))

        streams.update()
        return True


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
        return self._implementation.transform(img, self.config.matrix, self._design_shape)

    def coordinate(self, coordinate: Coo) -> Coo:
        """Transform a design coordinate to a video coordinate
        """
        og_co = coordinate.copy()
        co = self._implementation.coordinate(coordinate, self._inverse, self._video_shape[::-1])  # todo: ugh
        return co

    def inverse(self, img: np.ndarray) -> np.ndarray:
        return self._implementation.transform(img, self._inverse, self._video_shape)

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
        self.set_implementation(self.config.type)
        if self.config.data is None:
            self.config(data=self._implementation._config_class())

    @property
    def config(self) -> FilterHandlerConfig:
        return self._config

    @backend.expose(backend.get_filter_mean_color)
    def mean_color(self) -> HsvColor:
        return self._implementation.mean_color(self.config.data)

    @backend.expose(backend.set_filter_parameters)
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

    @backend.expose(backend.get_filter_parameters)
    def get_filter(self) -> FilterConfig:
        assert isinstance(self.config.data, FilterConfig)
        return self.config.data

    @backend.expose(backend.set_filter_implementation)
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
    _h: float
    _dpi: float

    _part: np.ndarray
    _rect: np.ndarray

    def __init__(
            self,
            mask: np.ndarray,
            name: str,
            config: MaskConfig = None,
            filter: FilterHandler = None,
            dpi: float = None,
            h: float = None,
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

        if h is None:
            if self.config.height is not None:
                self._h = self.config.height
            else:
                raise BackendSetupError(f'Mask {self.config.name} has no defined height.')
        else:
            self._h = h

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
    def h(self):
        return self._h

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
    _h: float

    def __init__(self, path: str, h: float, config: DesignFileHandlerConfig = None, mask_config: Tuple[MaskConfig,...] = None):
        super(DesignFileHandler, self).__init__(config)
        self._h = h
        if not os.path.isfile(path):
            raise FileNotFoundError

        self._path = path
        with self.caching():  # todo: maybe also do this in a separate thread? It's quite slow.
            self._overlay = self.peel_design(path)
            self._shape = (self._overlay.shape[1], self._overlay.shape[0])

            self._masks = []
            for i, (mask, name) in enumerate(zip(*self.read_masks(path))):
                if mask_config is not None and len(mask_config) >= i+1:  # handle case len(mask_config) < len(self.read_masks(path))
                    self._masks.append(Mask(mask, name, mask_config[i], h=self._h, dpi=self.config.dpi))
                else:
                    self._masks.append(Mask(mask, name, h=self._h, dpi=self.config.dpi))

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

        if not self.config.keep_renders:
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

    def __init__(self, mask: Mask):
        self.mask = mask
        self.filter = mask.filter

        super(MaskFunction, self).__init__(
            (self.mask, self.filter)
        )

        self._skip = mask.config.skip
        self._ready = mask.config.ready

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
        return None


@extend(FeatureType)
class PixelSum(MaskFunction):
    def _function(self, frame: np.ndarray) -> Any:
        return area_pixelsum(frame)


@extend(FeatureType)
class Volume_uL(MaskFunction):
    _parameters = ('h',)

    def _function(self, frame: np.ndarray) -> Any:
        return area_pixelsum(frame) / (self.mask.dpi / 25.4) ** 2 * self.mask.h * 1e3


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

    def can_launch(self) -> bool:
        if self.config.video_path is not None \
                and self.config.design_path is not None:
            return os.path.isfile(self.config.video_path) \
                   and os.path.isfile(self.config.design_path)
        else:
            return False

    def can_run(self) -> bool:
        if self.can_launch():
            return self.ok_to_run
        else:
            return False

    def _launch(self):
        # todo: query history for
        #  - combination of video file & design file
        #       * hash files & resolve to ids (should be a History method)
        #       * get latest entry in 'analyses' table matching both
        #           - get transform & filter settings from entry
        #           - if either is not present, leave empty
        #           * (optional: if either is not present, look back until
        #              it's found, to a maximum number of entries)

        self.load_config()  # todo: replace with ^
        log.debug(f'{self.__class__.__name__}: launch nested instances.')
        self.video = VideoFileHandler(self.config.video_path, self.stream_methods, self.config.video)  # todo: stream_methods list should be generated automatically
        self.video.set_requested_frames(list(self.frame_numbers()))
        self.design = DesignFileHandler(self.config.design_path, self.config.height, self.config.design, self.config.masks)
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

        # Initialize FeatureSets
        self._get_featuresets()

        # todo: maybe add some stuff to do this automagically
        backend.expose(backend.get_frame)(self.get_transformed_frame)
        backend.expose(backend.get_inverse_overlaid_frame)(self.get_inverse_overlaid_frame)
        backend.expose(backend.get_overlaid_frame)(self.get_frame_overlay)
        backend.expose(backend.get_state_frame)(self.get_state_frame)
        backend.expose(backend.get_colors)(self.get_colors)

        if self.model is not None:
            self.model.store()

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

        for fs, feature in zip(self._featuresets.values(), self.config.features):
            self.results[str(feature)] = pd.DataFrame(
                [], columns=['time'] + [f.name for f in fs.features], index=list(self.frame_numbers())
            )

    def configure(self):
        if self._gui is not None:
            self._gui.get(gui.open_setupwindow)()

    def align(self):
        if self._gui is not None:
            self._gui.get(gui.open_transformwindow)()

    def pick(self, index: int):
        if self._gui is not None:
            self._gui.get(gui.open_filterwindow)(index)
    # </backend shouldn't care about this>

    @backend.expose(backend.get_config)
    def get_config(self) -> dict:
        return self.config.to_dict()

    @backend.expose(backend.set_config)
    def set_config(self, config: dict) -> bool:
        with self.lock():
            if True:  # todo: sanity check
                log.debug(f"Setting VideoAnalyzerConfig to {config}")

                previous_features = copy.copy(self.config.features)

                self._config(**config)

                # Check for changes in features
                if previous_features != self.config.features:
                    log.debug('updating featuresets')
                    self._get_featuresets()

                # Check for state transitions
                if self._state == AnalyzerState.INCOMPLETE:
                    if self.can_launch():
                        self._state = AnalyzerState.CAN_LAUNCH
                if self._state == AnalyzerState.LAUNCHED:
                    if self.can_run():
                        self._state = AnalyzerState.CAN_RUN
                return True

    @stream
    @backend.expose(backend.get_frame)  # todo: would like to have some kind of 'deferred expose' decorator?
    def get_transformed_frame(self, frame_number: Optional[int] = None) -> np.ndarray:
        return self.transform(self.video.read_frame(frame_number))

    @backend.expose(backend.get_inverse_transformed_overlay)
    def get_inverse_transformed_overlay(self) -> np.ndarray:
        return self.transform.inverse(self.design.overlay())

    @backend.expose(backend.get_overlaid_frame)
    def get_frame_overlay(self, frame_number: int) -> np.ndarray:
        return self.design.overlay_frame(
            self.get_transformed_frame(frame_number))

    @backend.expose(backend.get_colors)  # todo: per feature in each feature set; maybe better as a dict instead of a list of tuples?
    def get_colors(self) -> List[Tuple[HsvColor, ...]]:
        return [featureset.get_colors() for featureset in
                self._featuresets.values()]

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
        return cv2.cvtColor(  # todo: loads of unnecessary color conversion here
            overlay(
                cv2.cvtColor(self.video.read_frame(frame_number), cv2.COLOR_HSV2BGR),
                self.transform.inverse(self.design.overlay()),
                alpha=self.design.config.overlay_alpha
            ), cv2.COLOR_BGR2HSV)

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
        elif len(hits) == 0:
            log.debug(f"no hit for {click.idx}")
        elif len(hits) > 1:
            message = f"Multiple valid options: {[hit.name for hit in hits]}. Select a point where masks don't overlap."
            response['message'] = message
            log.warning(message)
        return response


    @stream
    @backend.expose(backend.get_state_frame)
    def get_state_frame(self, frame_number: Optional[int] = None, featureset: Optional[int] = 0) -> np.ndarray:
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

        if self.model is None:
            log.warning(f"no model provided to {self}; data may be lost")

        with self.lock(), self.time():
            self._get_featuresets()
            self.save_config()

            log.debug(f"Analyzing with features: {[f for f in self._featuresets]}.")

            # if self._gui is not None:
            #     update_callback = self._gui.get(gui.update_progresswindow)  # todo: move this to LegacyVideoAnalyzer
            #     self._gui.get(gui.open_progresswindow)()
            # else:
            #     def update_callback(*args, **kwargs): pass  # todo: move this to LegacyVideoAnalyzer

            for fn in self.frame_numbers():
                if self._cancel.is_set():
                    break
                self.calculate(fn) #, update_callback)
                self._progress = fn / self.video.frame_count

            if self.model is not None:
                # Save results & configuration to database
                self.model.store()
        if not self._cancel.is_set():
            self._state = AnalyzerState.DONE
            return True
        else:
            self._cancel.clear()
            return False

    def load_config(self, path: str = None):  # todo: look in history instead of file next to video
        """Load video analysis configuration
        """
        if path is None and self.config.video_path:
            path = self.config.video_path

        if path is not None:
            path = os.path.splitext(path)[0] + __meta_ext__  # todo:
            assert path is not None
            if os.path.isfile(path):
                # todo: this is a temporary workaround to not overwrite current configuration ~ .meta file
                #        should be done by setting the fields to None & more in-depth config handling in BackendInstance._configure
                config = load(path) # todo: in isimple.og, make LegacyVideoAnalyzer(VideoAnalyzer) that implements these
                config.name = self.config.name
                config.description = self.config.description
                config.video_path = self.config.video_path
                config.design_path = self.config.design_path
                config.dt = self.config.dt
                config.Nf = self.config.Nf
                config.frame_interval_setting = self.config.frame_interval_setting
                config.height = self.config.height

                self._configure(config)

        else:
            log.warning(f"No path provided to `load_config`; no video file either.")

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


def init(config: Config) -> BaseVideoAnalyzer:
    mapping = {
        VideoAnalyzerConfig: VideoAnalyzer
    }

    return mapping[type(config)](config)
