import unittest

import os
import json

from typing import _GenericAlias, Union, Tuple, List, Dict  #type: ignore

from isimple.core.util import resolve_type_to_most_specific, get_schema
from isimple.core.config import VideoAnalyzerConfig

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
            Union[dict, str, int],
            resolve_type_to_most_specific(
                Union[dict, str, int]
            )
        )
        self.assertEqual(
            Tuple[List[Dict[str, Union[dict, str, int]]],...],
            resolve_type_to_most_specific(
                Tuple[List[Dict[str, Union[dict, str, int]]],...]
            )
        )


class SchemaTest(unittest.TestCase):
    def test_dump_schema(self):
        path = '../isimple/core/schemas/VideoAnalyzerConfig.json'
        try:
            os.remove(path)
        except FileNotFoundError:
            pass

        get_schema(VideoAnalyzerConfig)

        self.assertTrue(os.path.isfile(path))

        with open(path, 'r') as f:
            schema = json.load(f)

        # Is the schema 'legal'?


        # Are all Config attributes present in the schema's properties?
        self.assertListEqual(
            [k for k in VideoAnalyzerConfig.__dict__.keys() if k[0] != '_'],
            [k for k in schema['properties'].keys()]
        )

        # Are all references in the


