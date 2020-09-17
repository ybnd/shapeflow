import unittest

import os
import json

from typing import _GenericAlias, Union, Tuple, List, Dict, Optional  #type: ignore

from shapeflow.util.meta import resolve_type_to_most_specific
from shapeflow.config import VideoAnalyzerConfig


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
