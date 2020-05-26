import unittest

import os

from isimple.video import *
from isimple.core.config import Factory, dataclass, field, Config
from isimple.core import EnforcedStr
from isimple.core.interface import FilterType

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
        @dataclass
        class DummyConfig(Config):
            a: int = field(default=123)
            b: str = field(default='abc')
            c: tuple = field(default=(4, 5, 6))
            d: float = field(default=7.89)

        conf = DummyConfig(b='not abc')

        self.assertEqual(123, conf.a)
        self.assertEqual('not abc', conf.b)
        self.assertEqual((4,5,6), conf.c)
        self.assertEqual(7.89, conf.d)

        conf(d=1.23, a=789)

        self.assertEqual(789, conf.a)
        self.assertEqual('not abc', conf.b)
        self.assertEqual((4, 5, 6), conf.c)
        self.assertEqual(1.23, conf.d)

    def test_instance_attributes(self):
        @dataclass
        class DummyConfig(Config):
            a: int = field(default=123)
            b: str = field(default='abc')
            c: tuple = field(default=(4, 5, 6))
            d: float = field(default=7.89)

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

        @dataclass
        class DummyResolveConfig(Config):
            a: np.ndarray = field(default=np.array([4,5,6,7]))
            b: DummyEnforcedStr = field(default_factory=DummyEnforcedStr)

        original = DummyResolveConfig()
        loaded = DummyResolveConfig(**original.to_dict())

        self.assertIsInstance(loaded.a, np.ndarray)
        self.assertIsInstance(loaded.b, DummyEnforcedStr)

    def test_nested_resolution(self):
        class DummyEnforcedStr(EnforcedStr):
            _options = ['option1', 'option2']

        @dataclass
        class DummyNestedConfig(Config):
            a: np.ndarray = field(default=np.array([4,5,6,7]))
            b: DummyEnforcedStr = field(default_factory=DummyEnforcedStr)

        @dataclass
        class DummyResolveConfig(Config):
            c: DummyNestedConfig = field(default_factory=DummyNestedConfig)

        original = DummyResolveConfig()
        loaded = DummyResolveConfig(**original.to_dict())

        self.assertIsInstance(loaded.c, DummyNestedConfig)
        self.assertIsInstance(loaded.c, DummyNestedConfig)
        self.assertIsInstance(loaded.c, DummyNestedConfig)


class BackendConfigTest(unittest.TestCase):
    def test_videoanalyzerconfig(self):
        vac = VideoAnalyzerConfig(__VIDEO__, __DESIGN__)

        self.assertEqual(__VIDEO__, vac.video_path)
        self.assertEqual(__DESIGN__, vac.design_path)

        self.assertEqual('Nf', vac.frame_interval_setting)

    def test_instantiate_factories(self):
        vac = VideoAnalyzerConfig(__VIDEO__, __DESIGN__)

        self.assertEqual(FrameIntervalSetting(), vac.frame_interval_setting)
        self.assertIsInstance(vac.frame_interval_setting, FrameIntervalSetting)

        vac = VideoAnalyzerConfig(__VIDEO__, __DESIGN__, FrameIntervalSetting('dt'))
        self.assertEqual(FrameIntervalSetting(), vac.frame_interval_setting)
        self.assertIsInstance(vac.frame_interval_setting, FrameIntervalSetting)
