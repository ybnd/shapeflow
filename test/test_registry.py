import unittest

from typing import Callable

from isimple.core.common import Endpoint, Registry, ImmutableRegistry, RegistryEntry, EndpointRegistry, Manager


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


class RegistryTest(unittest.TestCase):
    def setUp(self) -> None:
        class TestReg(Registry):
            Reg1 = RegistryEntry()
            Reg2 = RegistryEntry()

        self.registry = TestReg()

    def test_create_registry(self):
        self.assertEqual(
            [self.registry.Reg1, self.registry.Reg2],
            self.registry._entries
        )


class EndpointRegistryTest(unittest.TestCase):
    def setUp(self) -> None:
        class TestEndpoints(ImmutableRegistry):
            ep1 = Endpoint(Callable[[int, float], str])
            ep2 = Endpoint(Callable[[], bool])
            ep3 = Endpoint(Callable[[int, int], float])

        self.registry = TestEndpoints(EndpointRegistry())

    def tearDown(self) -> None:
        del self.registry

    def test_expose_endpoints(self):
        @self.registry.expose(self.registry.ep1)
        def dummy1(a: int, b: float) -> str:
            return str(a + b)

        @self.registry.expose(self.registry.ep2)
        def dummy2() -> bool:
            return True

        self.assertEqual(
            [self.registry.ep1, self.registry.ep2], self.registry.endpoints()
        )

    def test_list_endpoints(self):
        self.assertEqual(
            [], self.registry.endpoints()
        )

        @self.registry.expose(self.registry.ep1)
        def dummy1(a: int, b: float) -> str:
            return str(a + b)

        @self.registry.expose(self.registry.ep2)
        def dummy2() -> bool:
            return True

        self.assertEqual(
            [self.registry.ep1, self.registry.ep2], self.registry.endpoints()
        )

    def test_collisions(self):
        self.assertEqual(
            [], self.registry.endpoints()
        )

        @self.registry.expose(self.registry.ep1)
        def dummy1(a: int, b: float) -> str:
            return str(a + b)

        @self.registry.expose(self.registry.ep1)
        def dummy2(a: int, b: float) -> str:
            return str(a + b)

        self.assertEqual(
            [self.registry.ep1], self.registry.endpoints()
        )


class ManagerTest(EndpointRegistryTest):
    def setUp(self) -> None:
        super(ManagerTest, self).setUp()

        class I(object):
            pass

        class TestManager(Manager):
            _endpoints = self.registry
            _instance_class = I

        self.TM = TestManager
        self.I = I

    def tearDown(self):
        del self.TM

    def test_instance_mapping_separate(self):
        class A(self.I):
            @self.registry.expose(self.registry.ep1)
            def dummy1(self, a: int, b: float) -> str:
                return str(a + b)

        class B(self.I):
            @self.registry.expose(self.registry.ep2)
            def dummy2(self) -> bool:
                return True

        tm = self.TM()
        tm.a = A()
        tm.b = B()

        tm._gather_instances()

        self.assertEqual(
            tm.a.dummy1, tm.get_callback(self.registry.ep1)
        )
        self.assertEqual(
            tm.b.dummy2, tm.get_callback(self.registry.ep2)
        )
        self.assertEqual(
            None, tm.get_callback(self.registry.ep3)
        )

    def test_instance_mapping_list(self):
        class A(self.I):
            @self.registry.expose(self.registry.ep1)
            def dummy1(self, a: int, b: float) -> str:
                return str(a + b)

        class B(self.I):
            @self.registry.expose(self.registry.ep2)
            def dummy2(self) -> bool:
                return True

        tm = self.TM()
        tm.i = [A(), B()]

        tm._gather_instances()

        self.assertEqual(
            tm.i[0].dummy1, tm.get_callback(self.registry.ep1)
        )
        self.assertEqual(
            tm.i[1].dummy2, tm.get_callback(self.registry.ep2)
        )
        self.assertEqual(
            None, tm.get_callback(self.registry.ep3)
        )

    def test_instance_mapping_list_collision(self):
        class A(self.I):
            @self.registry.expose(self.registry.ep1)
            def dummy1(self, a: int, b: float) -> str:
                return str(a + b)

        class B(self.I):
            @self.registry.expose(self.registry.ep2)
            def dummy2(self) -> bool:
                return True

            @self.registry.expose(self.registry.ep1)
            def dummy1(self, a: int, b: float) -> str:
                return str(a + b)

        tm = self.TM()
        tm.i = [A(), B()]

        tm._gather_instances()

        self.assertEqual(
            tm.i[0].dummy1, tm.get_callback(self.registry.ep1)
        )
        self.assertEqual(
            tm.i[0].dummy1, tm.get_callback(self.registry.ep1, 0)
        )
        self.assertEqual(
            tm.i[1].dummy1, tm.get_callback(self.registry.ep1, 1)
        )
        self.assertEqual(
            tm.i[1].dummy2, tm.get_callback(self.registry.ep2)
        )
        self.assertEqual(
            None, tm.get_callback(self.registry.ep3)
        )

    def test_instance_mapping_self(self):
        class A(self.I):
            @self.registry.expose(self.registry.ep1)
            def dummy1(self, a: int, b: float) -> str:
                return str(a + b)

        class TM2(self.TM):
            @self.registry.expose(self.registry.ep2)
            def dummy2(self) -> bool:
                return True

        tm = TM2()
        tm.a = A()

        tm._gather_instances()

        self.assertEqual(
            tm.a.dummy1, tm.get_callback(self.registry.ep1)
        )
        self.assertEqual(
            tm.dummy2, tm.get_callback(self.registry.ep2)
        )
        self.assertEqual(
            None, tm.get_callback(self.registry.ep3)
        )
