import unittest

from isimple.video import *
from isimple.core.config import EnforcedStr, Factory, dataclass, Config
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
            a: int = 123
            b: str = 'abc'
            c: tuple = (4, 5, 6)
            d: float = 7.89

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
            a: int = 123
            b: str = 'abc'
            c: tuple = (4, 5, 6)
            d: float = 7.89

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


class BackendConfigTest(unittest.TestCase):
    def test_videoanalyzerconfig(self):
        vac = VideoAnalyzerConfig(__VIDEO__, __DESIGN__)

        self.assertEqual(__VIDEO__, vac.video_path)
        self.assertEqual(__DESIGN__, vac.design_path)

        self.assertEqual('dt', vac.frame_interval_setting)

    def test_instantiate_factories(self):
        vac = VideoAnalyzerConfig(__VIDEO__, __DESIGN__)

        self.assertEqual(FrameIntervalSetting(), vac.frame_interval_setting)
        self.assertIsInstance(vac.frame_interval_setting, FrameIntervalSetting)

        vac = VideoAnalyzerConfig(__VIDEO__, __DESIGN__, FrameIntervalSetting('dt'))
        self.assertEqual(FrameIntervalSetting(), vac.frame_interval_setting)
        self.assertIsInstance(vac.frame_interval_setting, FrameIntervalSetting)


__YAML_CONFIG__ = f'''
version: '0.2'
video_path: {__VIDEO__}
design_path: {__DESIGN__}
frame_interval_setting: dt
dt: 10.000
video:
  do_cache: True
  do_background: False
design:
  do_cache: False
  do_background: False
  render_dir: .renders
transform:
  type: perspective
  matrix: [[1,0,100],[0,1,200],[0,0,1]]
masks:
  - height: 0.127e-3
    filter: 
      type: hsv range
      filter:
        radius: (15, 50, 25)
  - height: 0.306e-3
    filter: 
      type: hsv range
      filter: 
        radius: (30, 10, 10)
features:
  - pixel sum
'''

class VideoAnalyzerConfigTest(unittest.TestCase):
    yaml = 'config.yaml'

    def setUp(self):
        if os.path.isfile(self.yaml):
            os.remove(self.yaml)

        with open(self.yaml, 'w+') as f:
            f.write(__YAML_CONFIG__)

    def tearDown(self):
        if os.path.isfile(self.yaml):
            os.remove(self.yaml)

    def test_load(self):
        config = load(self.yaml)

        self.assertEqual(10, config.dt)
        self.assertEqual(0.153e-3, config.height)
        self.assertEqual(False, config.design.do_background)
        self.assertEqual(True, config.video.do_cache)
        self.assertEqual(0.127e-3, config.masks[0].height)

    def test_dump(self):
        dump(load(self.yaml), 'temp.yaml')

        with open(self.yaml, 'r') as f:
            cs = f.read()

        if os.path.isfile('temp.yaml'):
            os.remove('temp.yaml')