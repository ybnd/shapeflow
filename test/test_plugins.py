import unittest

import abc
from typing import Type, Dict, List

import cv2
import numpy as np

from shapeflow.maths.coordinates import Roi, Coo
from shapeflow.maths.images import ckernel
from shapeflow.core.config import Factory
from shapeflow.config import TransformType, ConfigType, TransformConfig
from shapeflow.plugins import *
from shapeflow.video import *


__VIDEO__ = 'test.mp4'
__DESIGN__ = 'test.svg'


# Point to right files in Travis CI build
if os.getcwd() == '/home/travis/build/ybnd/shapeflow':
    __VIDEO__ = 'test/' + __VIDEO__
    __DESIGN__ = 'test/' + __DESIGN__


class PluginRegistrationTest(unittest.TestCase):
    def test_valid_extension(self):
        @extend(TransformType)
        class SomeTransform(TransformInterface):
            _config_class = TransformConfig

            def validate(self, matrix: Optional[np.ndarray]) -> bool:
                return True

            def from_coordinates(self, roi: Roi, from_shape: tuple) -> np.ndarray:
                return np.array([])

            def to_coordinates(self, to_shape: tuple) -> np.ndarray:
                return np.array([])

            def estimate(self, roi: Roi, from_shape: tuple, to_shape: tuple) -> np.ndarray:
                return np.array([])

            def transform(self, matrix: np.ndarray, img: np.ndarray, shape: Tuple[int, int]) -> np.ndarray:
                return np.array([])

            def coordinate(self, matrix: np.ndarray, coordinate: ShapeCoo, shape: Tuple[int, int]) -> ShapeCoo:
                return coordinate

        TransformType('SomeTransform').get()()

    def test_abstract_extension(self):
        @extend(TransformType)
        class SomeTransform(TransformInterface):
            pass

        self.assertRaises(
            TypeError,
            FeatureType('SomeFeature').get()
        )

    def test_invalid_extension_type(self):
        def _define_object_as_transform():
            @extend(TransformType)
            class SomeTransform(object):
                pass

        def _define_filter_as_transform():
            @extend(TransformType)
            class SomeTransform(FilterInterface):
                pass

        self.assertRaises(
            TypeError,
            _define_object_as_transform
        )
        self.assertRaises(
            TypeError,
            _define_filter_as_transform
        )


class BaseTransformTest(abc.ABC, unittest.TestCase):
    transform: TransformInterface

    valid_matrices: List[np.ndarray]
    invalid_matrices: List[Optional[np.ndarray]]

    valid_estimations: List[Tuple[Roi, Tuple[int, int], Tuple[int, int]]]
    invalid_estimations: List[Tuple[Roi, Tuple[int, int], Tuple[int, int]]]

    img: np.ndarray = cv2.cvtColor(
        np.random.randint(0, 255, (64, 64, 3), dtype=np.uint8),
        cv2.COLOR_BGR2HSV
    )
    coordinate: ShapeCoo = ShapeCoo(x=0.3, y=0.6, shape=(64, 64))

    def test_validate(self):
        for matrix in self.valid_matrices:
            self.assertTrue(
                self.transform.validate(matrix)
            )
        for matrix in self.invalid_matrices:
            self.assertFalse(
                self.transform.validate(matrix)
            )

    def test_estimate(self):
        for roi, from_shape, to_shape in self.valid_estimations:
            matrix = self.transform.estimate(roi, from_shape, to_shape)
            self.assertTrue(
                self.transform.validate(matrix)
            )
        for roi, from_shape, to_shape in self.invalid_estimations:
            self.assertIsNone(
                self.transform.estimate(roi, from_shape, to_shape)
            )

    def test_transform(self):
        self.transform.transform(
            self.transform.estimate(*self.valid_estimations[0]),
            self.img, self.valid_estimations[0][1]
        )

    def test_coordinate(self):
        self.transform.coordinate(
            np.linalg.inv(self.transform.estimate(*self.valid_estimations[0])),
            self.coordinate, self.valid_estimations[0][2]
        )


class BaseFilterTest(abc.ABC, unittest.TestCase):
    filter: FilterInterface
    config_type: Type[FilterConfig]

    valid_set_filter: List[Tuple[FilterConfig, HsvColor]]
    invalid_set_filter: List[Tuple[FilterConfig, Any]]

    valid_filter: List[FilterConfig]
    invalid_filter: List[FilterConfig]

    ready_filter: List[FilterConfig]
    not_ready_filter: List[FilterConfig]

    img: np.ndarray = cv2.cvtColor(
        np.random.randint(0, 255, (64, 64, 3), dtype=np.uint8),
        cv2.COLOR_BGR2HSV
    )

    def test_set_filter(self):
        for filter, color in self.valid_set_filter:
            filter = self.filter.set_filter(filter, color)
            self.filter.mean_color(filter)

        for filter, color in self.invalid_set_filter:
            self.assertRaises(
                ValueError,
                self.filter.set_filter, filter, color
            )

    def test_filter(self):
        for filter in self.valid_filter:
            self.filter.filter(filter, self.img)

        for filter in self.invalid_filter:
            self.assertRaises(
                ValueError,
                self.filter.filter, filter, self.img
            )

    def test_ready(self):
        for filter in self.ready_filter:
            self.assertTrue(filter.ready)
        for filter in self.not_ready_filter:
            self.assertFalse(filter.ready)


class BaseMaskFunctionTest(unittest.TestCase):
    design: DesignFileHandler
    mask: Mask

    feature: MaskFunction
    feature_type: Type[Feature]
    parameters_type: Type[FeatureConfig]

    img: np.ndarray = cv2.cvtColor(
        np.random.randint(0, 255, (100, 100, 3), dtype=np.uint8),
        cv2.COLOR_BGR2HSV
    )

    valid_parameters: List[FeatureConfig] = []

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        mask_img = np.zeros(self.img.shape[:2], dtype=np.uint8)
        mask_img[0:25, 0:25] = ckernel(25)

        self.design = DesignFileHandler(__DESIGN__, DesignFileHandlerConfig(dpi=400))

        self.mask = Mask(
            design=self.design,
            mask=mask_img,
            name='test mask',
            config=MaskConfig(),
            filter=FilterHandler(),
        )
        assert issubclass(self.feature_type, MaskFunction)
        self.feature = self.feature_type(self.mask, self.parameters_type())

    def _test_value(self):
        self.feature.value(self.img)

    def test_value(self):
        self._test_value()

        for parameters in self.valid_parameters:
            self.feature._config = parameters
            self._test_value()

        self.feature._config = None

    def _test_state(self):
        self.feature._skip = True
        self.feature.state(self.img, np.zeros(self.img.shape))

        self.feature._skip = False
        self.feature._ready = False
        self.feature.state(self.img, np.zeros(self.img.shape))

        self.feature._skip = False
        self.feature._ready = True
        self.feature.state(self.img, np.zeros(self.img.shape))

    def test_state(self):
        self._test_state()

        for parameters in self.valid_parameters:
            self.feature._config = parameters
            self._test_state()

        self.feature._config = None


class PerspectiveTransformTest(BaseTransformTest):
    transform = TransformType('PerspectiveTransform').get()()
    config_type = TransformType('PerspectiveTransform').get().config_class()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.valid_matrices = [
            np.array([[1, 0, 0], [0, 1, 0], [0, 0, 1]]),
        ]
        self.invalid_matrices = [
            None,
            np.array([1]),
            np.array([[1]]),
            np.array([[1, 0], [0, 1]]),
            np.array([[1, 0, 0], [0, 1, 0]]),
            np.array([[1, 0], [0, 1], [0, 0]]),
            np.array([[0, 0, 0], [0, 0, 0], [0, 0, 1]]),
        ]

        self.valid_estimations = [
            (
                Roi(BL=Coo(x=0.8, y=0.2), TL=Coo(x=0.8, y=0.8),
                    TR=Coo(x=0.2, y=0.8), BR=Coo(x=0.2, y=0.2)),
                (64,64),
                (100,100)
            ),
        ]
        self.invalid_estimations = [
            (
                Roi(BL=Coo(x=0.2, y=0.2), TL=Coo(x=0.2, y=0.2),
                    TR=Coo(x=0.2, y=0.2), BR=Coo(x=0.2, y=0.2)),
                (64, 64),
                (100, 100)
            ),
            (
                Roi(BL=Coo(x=0.8, y=0.2), TL=Coo(x=0.8, y=0.8),
                    TR=Coo(x=0.2, y=0.8), BR=Coo(x=0.2, y=0.2)),
                (64, 64),
                (0, 0)
            ),
        ]


class HsvRangeFilterTest(BaseFilterTest):
    filter = FilterType('HsvRangeFilter').get()()
    config_type = FilterType('HsvRangeFilter').get().config_class()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.valid_set_filter = [
            (
                self.config_type(),
                HsvColor(h=50, s=50, v=50)
            ),
        ]
        self.invalid_set_filter = [
            (
                self.config_type(),
                None
            ),
            (
                self.config_type(),
                (50,50,50)
            ),
        ]

        self.valid_filter = [
            self.config_type(range=HsvColor(h=20), color=HsvColor(h=50)),
            self.config_type(range=HsvColor(h=50), color=HsvColor(h=20)),
            self.config_type(range=HsvColor(h=50), color=HsvColor(h=170)),
        ]
        self.invalid_filter = [
        ]

        self.ready_filter = [
            self.config_type(color=HsvColor(h=20, s=20, v=20)),
        ]
        self.not_ready_filter = [
            self.config_type(),
        ]


class PixelSumTest(BaseMaskFunctionTest):
    feature_type = FeatureType('PixelSum').get()
    parameters_type = FeatureConfig


class Area_mm2Test(BaseMaskFunctionTest):
    feature_type = FeatureType('Area_mm2').get()
    parameters_type = FeatureConfig


class Volume_uLTest(BaseMaskFunctionTest):
    feature_type = FeatureType('Volume_uL').get()
    parameters_type = FeatureType('Volume_uL').get().config_class()


# don't run abstract test cases
del BaseTransformTest
del BaseFilterTest
del BaseMaskFunctionTest
