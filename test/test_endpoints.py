import unittest

from typing import Callable

from shapeflow.core import Endpoint, Dispatcher
from shapeflow.util.meta import bind, unbind
from shapeflow.api import _CacheDispatcher, _DatabaseDispatcher, \
    _VideoAnalyzerManagerDispatcher, _FilesystemDispatcher, \
    _VideoAnalyzerDispatcher, ApiDispatcher


class EndpointTest(unittest.TestCase):
    def test_create_endpoint(self):
        def dummy1(a: int, b: float) -> str:
            return str(a + b)

        def dummy2() -> bool:
            return True

        ep1 = Endpoint(Callable[[int, float], str])
        ep2 = Endpoint(Callable[[], bool])
        self.assertEqual(Callable[[int, float], str], ep1._signature)
        self.assertEqual(Callable[[], bool], ep2._signature)

        self.assertTrue(ep1.compatible(dummy1))
        self.assertTrue(ep2.compatible(dummy2))
        self.assertFalse(ep2.compatible(dummy1))
        self.assertFalse(ep1.compatible(dummy2))

    def test_create_illegal_endpoint(self):
        def dummy_untyped():
            pass

        self.assertRaises(TypeError, Endpoint, dummy_untyped)
        self.assertRaises(TypeError, Endpoint, lambda x: x)
        self.assertRaises(TypeError, Endpoint)
        self.assertRaises(TypeError, Endpoint, '')


class DispatcherTest(unittest.TestCase):
    def test_single_dispatcher(self):
        class TestDispatcher(Dispatcher):
            dummy1 = Endpoint(Callable[[], None])
            dummy2 = Endpoint(Callable[[str], int])

        temp_td = TestDispatcher()

        class Test(object):
            @temp_td.dummy1.expose()
            def dummy1_method(self) -> None:
                return None

            @temp_td.dummy2.expose()
            def dummy2_method(self, s: str) -> int:
                return int(s)

        self.assertTrue(hasattr(temp_td, 'dummy1'))
        self.assertTrue(hasattr(temp_td, 'dummy2'))

        # methods not in address_space until isntance is bound to Dispatcher
        self.assertNotIn('dummy1', temp_td.address_space)
        self.assertNotIn('dummy2', temp_td.address_space)

        test = Test()
        td = TestDispatcher(test)

        # methods not in address_space until isntance is bound to Dispatcher
        self.assertIn('dummy1', td.address_space)
        self.assertIn('dummy2', td.address_space)

        # the endpoints don't change (class-level)
        self.assertEqual(temp_td.dummy1, td.dummy1)
        self.assertEqual(temp_td.dummy2, td.dummy2)

        # address_space methods refer to bound methods
        self.assertEqual(test.dummy1_method, td.address_space['dummy1'])
        self.assertEqual(test.dummy2_method, td.address_space['dummy2'])
        self.assertEqual(Test.dummy1_method, unbind(td.address_space['dummy1']))
        self.assertEqual(Test.dummy2_method, unbind(td.address_space['dummy2']))

    def test_nested_dispatchers(self):
        class LeafDispatcher(Dispatcher):
            dummy4 = Endpoint(Callable[[], bool])

        class BranchDispatcher(Dispatcher):
            dummy3 = Endpoint(Callable[[], None])

            level2 = LeafDispatcher()

        class RootDispatcher(Dispatcher):
            dummy1 = Endpoint(Callable[[], None])
            dummy2 = Endpoint(Callable[[str], int])

            level1 = BranchDispatcher()

        # instantiate temporary dispatcher
        rd = RootDispatcher()

        class Test1(object):
            @rd.dummy1.expose()
            def dummy1_method(self) -> None:
                return None

            @rd.dummy2.expose()
            def dummy2_method(self, s: str) -> int:
                return int(s)

        class Test2(object):
            @rd.level1.dummy3.expose()
            def dummy3_method(self) -> None:
                return None

        class Test3(object):
            @rd.level1.level2.dummy4.expose()
            def dummy4_method(self) -> bool:
                return False

        # instantiate dispatcher with references to Test1-3
        test1 = Test1()
        test2 = Test2()
        test3 = Test3()

        rd._set_instance(test1)
        rd._add_dispatcher('level1', BranchDispatcher(test2))
        rd.level1._add_dispatcher('level2', LeafDispatcher(test3))

        print(rd.address_space)

        self.assertIn('dummy1', rd.address_space)
        self.assertIn('dummy2', rd.address_space)
        self.assertIn('level1/dummy3', rd.address_space)
        self.assertIn('level1/level2/dummy4', rd.address_space)

        self.assertIn('dummy3', rd.level1.address_space)
        self.assertIn('level2/dummy4', rd.level1.address_space)

        self.assertIn('dummy4', rd.level1.level2.address_space)

        self.assertEqual(
            rd.level1.level2.address_space['dummy4'],
            rd.address_space['level1/level2/dummy4']
        )

        self.assertEqual(
            rd.level1.address_space['dummy3'],
            rd.address_space['level1/dummy3']
        )
