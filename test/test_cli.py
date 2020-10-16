import os
import abc
from typing import List
import unittest
import unittest.mock

from ... import shapeflow


Args = List[str]


# Point to right file in Travis CI build
if os.getcwd() == '/home/travis/build/ybnd/shapeflow':
    SF = os.path.join(os.getcwd(), 'shapeflow.py')
else:
    SF = os.path.join(os.getcwd(), '..', 'shapeflow.py')


@unittest.mock.patch('subprocess.check_call')
def _mock_check_call(args: Args):
    pass


class ShapeflowTest(unittest.TestCase):
    def test_help(self):
        pass

    def test_