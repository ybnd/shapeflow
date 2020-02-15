import unittest

from typing import Callable, Any

from isimple.registry import Endpoint, Registry, ImmutableRegistry, RegistryEntry, EndpointRegistry




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

        self.assertTrue(ep1.isvalid(dummy1))
        self.assertTrue(ep2.isvalid(dummy2))
        self.assertFalse(ep2.isvalid(dummy1))
        self.assertFalse(ep1.isvalid(dummy2))

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

        self.endpoints = TestEndpoints()
        self.registry = EndpointRegistry()

    def test_expose_endpoints(self):
        @self.registry.expose(self.endpoints.ep1)
        def dummy1(a: int, b: float) -> str:
            return str(a + b)

        @self.registry.expose(self.endpoints.ep2)
        def dummy2() -> bool:
            return True

        self.assertEqual(
            [self.endpoints.ep1, self.endpoints.ep2], self.registry._entries
        )

    def test_list_endpoints(self):
        self.assertEqual(
            [], self.registry.endpoints()
        )

        @self.registry.expose(self.endpoints.ep1)
        def dummy1(a: int, b: float) -> str:
            return str(a + b)

        @self.registry.expose(self.endpoints.ep2)
        def dummy2() -> bool:
            return True

        self.assertEqual(
            [self.endpoints.ep1, self.endpoints.ep2], self.registry.endpoints()
        )

    def test_collisions(self):
        self.assertEqual(
            [], self.registry.endpoints()
        )

        @self.registry.expose(self.endpoints.ep1)
        def dummy1(a: int, b: float) -> str:
            return str(a + b)

        @self.registry.expose(self.endpoints.ep1)
        def dummy2(a: int, b: float) -> str:
            return str(a + b)

        self.assertEqual(
            [self.endpoints.ep1], self.registry.endpoints()
        )