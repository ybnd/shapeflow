import unittest

import os
import json

from typing import _GenericAlias, Union, Tuple, List, Dict, Optional  #type: ignore

from isimple.core.schema import resolve_type_to_most_specific, \
    get_config_schema, get_method_schema, schema
from isimple.config import VideoAnalyzerConfig


class ResolveTypeTest(unittest.TestCase):
    def test_specifiable_union(self):
        class MockType(object):
            pass

        class SpecificMockType(MockType):
            pass

        self.assertEqual(
            SpecificMockType,
            resolve_type_to_most_specific(
                Union[SpecificMockType, MockType, None]
            )
        )
        self.assertEqual(
            Tuple[List[Dict[str,SpecificMockType]],...],
            resolve_type_to_most_specific(
                Tuple[List[Dict[str,Union[SpecificMockType, MockType, None]]],...]
            )
        )

    def test_unspecifiable_union(self):
        self.assertEqual(
            dict,
            resolve_type_to_most_specific(
                Union[dict, str, int]
            )
        )
        self.assertEqual(
            Tuple[List[Dict[str, dict]],...],
            resolve_type_to_most_specific(
                Tuple[List[Dict[str, Union[dict, str, int]]],...]
            )
        )


class SchemaTest(unittest.TestCase):
    def test_get_schema_schema(self):
        s = schema(VideoAnalyzerConfig)

    def test_get_method_schema(self):
        def annotated_method(
                arg1: int,
                arg2: float,
                arg3: Optional[bool] = False,
                arg4: bool = None
        ) -> list:
            return []

        def unannotated_method(
                arg1,
                arg2: float,
                arg3: Optional[bool] = False,
                arg4: bool = None
        ) -> list:
            return []

        s = schema(annotated_method)

        self.assertRaises(TypeError, get_method_schema, unannotated_method)