import abc
import re
from typing import Tuple, Any, Optional, List, Type, Generator
import os

import numpy as np
import cv2

from OnionSVG import OnionSVG, check_svg

from isimple.core.util import frame_number_iterator
from isimple.core.common import Manager
from isimple.core.backend import BackendInstance, CachingBackendInstance, BackendManager, BackendSetupError
from isimple.core.features import Feature, FeatureSet
from isimple.core.meta import Factory, ColorSpace, FrameIntervalSetting

from isimple.maths.images import ckernel, to_mask, crop_mask, area_pixelsum

from isimple.endpoints import BackendEndpoints


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

    @backend.expose(backend.get_raw_frame)
    def read_frame(self, frame_number: int) -> Optional[np.ndarray]:
        return self._cached_call(self._read_frame, self.path, frame_number)


class VideoHandlerType(Factory):
    _mapping = {
        'opencv':   VideoFileHandler,
    }


class Transform(BackendInstance, abc.ABC):
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

    @backend.expose(backend.estimate_transform)
    def estimate(self, coordinates: List) -> None:
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


    def estimate(self, coordinates: List) -> None:
        pass

    def __call__(self, img: np.ndarray) -> np.ndarray:
        return img


class PerspectiveTransform(Transform):
    def set(self, transform: np.ndarray):
        self._transform = transform

    def estimate(self, coordinates: List) -> None:
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


class Filter(BackendInstance, abc.ABC):
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

    @backend.expose(backend.set_filter_from_color)
    def set_filter(self, clr: List) -> None:
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


class Mask(BackendInstance):
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
            assert isinstance(filter, Filter), BackendSetupError
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
            self._shape = self._overlay.shape

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


def frame_to_none(frame: np.ndarray) -> None:    # todo: this is dumb
    return None


class MaskFilterFunction(Feature):
    _function = staticmethod(frame_to_none)  # Override in child classes

    mask: Mask
    filter: Filter

    def __init__(self, mask: Mask, filter: Filter = None):
        if filter is None:
            assert isinstance(mask.filter, Filter), BackendSetupError
            filter = mask.filter

        self.mask = mask
        self.filter = filter

        super(MaskFilterFunction, self).__init__((mask, filter))

    def _guideline_color(self) -> np.ndarray:
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
    _gui: Manager

    video: VideoFileHandler
    design: DesignFileHandler
    transform: Transform

    featuresets: List[FeatureSet]

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
        'features':                 [VideoFeatureType('pixel_sum')],
        'video_type':               VideoHandlerType(),
        'design_type':              DesignHandlerType(),
        'transform_type':           TransformType(),
    }

    _args: dict

    def __init__(self, video_path: str = None, design_path: str = None, config: dict = None):  # todo: add optional feature list to override self._config.features
        super(VideoAnalyzer, self).__init__(config)

        self._args = ({
            'video_path': video_path,
            'design_path': design_path,
            'config': config
        })

        if video_path is not None and design_path is not None:
            self.launch()

    def launch(self):
        video_path = self._args['video_path']
        design_path = self._args['design_path']
        config = self._args['config']

        if video_path and design_path:
            self.video = self.video_type(video_path, config)
            self.design = self.design_type(design_path, config)
            self.transform = self.transform_type(self.video.shape, config)
            self.masks = self.design.masks
            self.filters = [mask.filter for mask in self.masks]

            self._gather_instances()  # todo: annoying that we have to call this one explicilty, but doing it at super.__init__ makes it less dynamic

            self.featuresets = [
                FeatureSet(
                    tuple(feature.get()(mask) for mask in self.design.masks)
                ) for feature in self.features
            ]
        else:
            raise ValueError("Either the video or the design wasn't provided")  # todo: make error message more specific

    @backend.expose(backend.configure)
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

    @backend.expose(backend.get_transformed_frame)
    def get_transformed_frame(self, frame_number: int) -> np.ndarray:
        return self.transform(self.video.read_frame(frame_number))# todo: depending on self.frame is dangerous in case we want to run this in a different thread

    @backend.expose(backend.get_transformed_overlaid_frame)
    def get_frame_overlay(self, frame_number: int) -> np.ndarray:
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

            V.append(values)   # todo: value values value ugh
            S.append(state)

        # todo: launch callbacks here

    def analyze(self):
        for fn in self.frame_numbers():
            self.calculate(fn)


class MultiVideoAnalyzer(BackendManager):
    pass