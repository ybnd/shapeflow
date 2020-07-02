import unittest

import yaml

from isimple.plugins.HsvRangeFilter import HsvRangeFilter
from isimple.video import *
from isimple.core.config import Factory, Field, BaseConfig, validator, VERSION, CLASS
from isimple.core import EnforcedStr
from isimple.core.interface import FilterType

from isimple.config import normalize_config

__VIDEO__ = 'test.mp4'
__DESIGN__ = 'test.svg'

# Point to right files in Travis CI build
if os.getcwd() == '/home/travis/build/ybnd/isimple':
    __VIDEO__ = 'test/' + __VIDEO__
    __DESIGN__ = 'test/' + __DESIGN__


class ColorSpace(EnforcedStr):
    _options = ['hsv', 'bgr', 'rgb']


class EnforcedStrTest(unittest.TestCase):
    def test_definitions(self):
        ColorSpace('rgb')
        FilterType('hsv range')

    def test_comparisons(self):
        self.assertEqual('hsv', ColorSpace('hsv'))
        self.assertEqual('hsv', ColorSpace('nope'))
        self.assertEqual(ColorSpace('hsv'), ColorSpace('hsv'))
        self.assertNotEqual(ColorSpace('hsv'), ColorSpace('bgr'))

    def test_factory(self):
        self.assertEqual(HsvRangeFilter, FilterType('hsv range').get())

    def test_subclassing(self):
        class TestEnfStr(EnforcedStr):
            _options = ['1', '2', '3']

        class TestFactory1(Factory):
            _mapping = {'z': 1, 'b': 2, 'a': 7}
            _default = 'b'

        class TestFactory2(Factory):
            _mapping = {'z': 1, 'b': 2, 'a': 7}

        self.assertEqual('3', TestEnfStr('3'))
        self.assertEqual('1', TestEnfStr('7'))

        self.assertEqual(7, TestFactory1('a').get())
        self.assertEqual(2, TestFactory1('').get())

        self.assertEqual(1, TestFactory2('').get())


class ConfigTest(unittest.TestCase):
    def test_from_kwargs(self):
        class DummyConfig(BaseConfig):
            a: int = Field(default=123)
            b: str = Field(default='abc')
            c: tuple = Field(default=(4, 5, 6))
            d: float = Field(default=7.89)

        conf = DummyConfig(b='not abc')

        self.assertEqual(123, conf.a)
        self.assertEqual('not abc', conf.b)
        self.assertEqual((4,5,6), conf.c)
        self.assertEqual(7.89, conf.d)

        conf.d = 1.23
        conf.a = 789

        self.assertEqual(789, conf.a)
        self.assertEqual('not abc', conf.b)
        self.assertEqual((4, 5, 6), conf.c)
        self.assertEqual(1.23, conf.d)

    def test_instance_attributes(self):
        class DummyConfig(BaseConfig):
            a: int = Field(default=123)
            b: str = Field(default='abc')
            c: tuple = Field(default=(4, 5, 6))
            d: float = Field(default=7.89)

        conf1 = DummyConfig()
        conf2 = DummyConfig()

        self.assertEqual(conf1.a, conf2.a)
        self.assertEqual(conf1.b, conf2.b)
        self.assertEqual(conf1.c, conf2.c)
        self.assertEqual(conf1.d, conf2.d)

        conf2.b = 'not abc'
        conf2.c = (7,8,9)

        self.assertEqual(conf1.a, conf2.a)
        self.assertNotEqual(conf1.b, conf2.b)
        self.assertNotEqual(conf1.c, conf2.c)
        self.assertEqual(conf1.d, conf2.d)


class ConfigResolutionTest(unittest.TestCase):
    def test_resolution(self):
        class DummyEnforcedStr(EnforcedStr):
            _options = ['option1', 'option2']

        class DummyResolveConfig(BaseConfig):
            a: list = Field(default=[4,5,6,7])
            b: DummyEnforcedStr = Field(default_factory=DummyEnforcedStr)

            _resolve_b = validator('b', allow_reuse=True)(BaseConfig._resolve_enforcedstr)

        original = DummyResolveConfig()
        loaded = DummyResolveConfig(**original.to_dict())

        self.assertIsInstance(loaded.a, list)
        self.assertIsInstance(loaded.b, DummyEnforcedStr)

    def test_nested_resolution(self):
        class DummyEnforcedStr(EnforcedStr):
            _options = ['option1', 'option2']

        class DummyNestedConfig(BaseConfig):
            a: list = Field(default=[4,5,6,7])
            b: DummyEnforcedStr = Field(default_factory=DummyEnforcedStr)

        class DummyResolveConfig(BaseConfig):
            c: DummyNestedConfig = Field(default_factory=DummyNestedConfig)

        original = DummyResolveConfig()
        loaded = DummyResolveConfig(**original.to_dict())

        self.assertIsInstance(loaded.c, DummyNestedConfig)


class BackendConfigTest(unittest.TestCase):
    def test_videoanalyzerconfig(self):
        vac = VideoAnalyzerConfig(video_path=__VIDEO__, design_path=__DESIGN__)

        self.assertEqual(__VIDEO__, vac.video_path)
        self.assertEqual(__DESIGN__, vac.design_path)

        self.assertEqual('Nf', vac.frame_interval_setting)

    def test_instantiate_factories(self):
        vac = VideoAnalyzerConfig(video_path=__VIDEO__, design_path=__DESIGN__)

        self.assertEqual(FrameIntervalSetting(), vac.frame_interval_setting)
        self.assertIsInstance(vac.frame_interval_setting, FrameIntervalSetting)

        vac = VideoAnalyzerConfig(video_path=__VIDEO__, design_path=__DESIGN__, frame_interval_setting=FrameIntervalSetting('Nf'))
        self.assertEqual(FrameIntervalSetting(), vac.frame_interval_setting)
        self.assertIsInstance(vac.frame_interval_setting, FrameIntervalSetting)


class VideoAnalyzerConfigTest(unittest.TestCase):
    def test_normalization(self):
        __OLD_CONFIG__ = 'old.meta'

        # Point to right files in Travis CI build
        if os.getcwd() == '/home/travis/build/ybnd/isimple':
            __OLD_CONFIG__ = 'test/' + __OLD_CONFIG__

        with open(__OLD_CONFIG__, 'r') as f:
            old_config = yaml.safe_load(f)

        VideoAnalyzerConfig(**normalize_config(old_config))

    def test_normalization_edge_cases(self):
        self.assertEqual(
            {},
            normalize_config({})
        )
        self.assertRaises(
            ValueError,
            normalize_config, {'something': 'but no class/version info'}
        )
        self.assertRaises(
            NotImplementedError,
            normalize_config, {VERSION: '0.3', CLASS: 'Unknown'}
        )


