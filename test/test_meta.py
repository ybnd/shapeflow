import unittest
from typing import List

import numpy as np

from isimple.meta import *
from isimple.meta import (
    __ext__, __video__, __design__, __height__, __timestep__, __coordinates__,
    __transform__, __order__, __colors__, __from__, __to__, __meta_sheet__,
)

from isimple.video import VideoAnalyzer, Area


__VIDEO__ = 'test.mp4'
__DESIGN__ = 'test.svg'

# Point to right files in Travis CI build
if os.getcwd() == '/home/travis/build/ybnd/isimple':
    __VIDEO__ = 'test/' + __VIDEO__
    __DESIGN__ = 'test/' + __DESIGN__

height = 1e-3
timestep = 5
coordinates = [[0,0] for i in range(4)]
transform = np.eye(3).tolist()
order = [0,1,2,3]

va = VideoAnalyzer(__VIDEO__, __DESIGN__, [Area])
masks = va.design._masks


class MetaTest(unittest.TestCase):
    colors: dict
    meta: dict

    def setUp(cls):
        cls.colors = {}
        for m in masks:
            m.filter_from = np.random.rand(1,3)
            m.filter_to = np.random.rand(1,3)
            cls.colors.update({
                m.name: {
                    __from__: m.filter_from.tolist(),
                    __to__: m.filter_to.tolist()
                }
            })

        cls.meta = {
            __video__: __VIDEO__,
            __design__: __DESIGN__,
            __height__: height,
            __timestep__: timestep,
            __coordinates__: coordinates,
            __transform__: transform,
            __order__: order,
            __colors__: cls.colors
        }

    def tearDown(self):
        pass

    def test_bundle(self):
        self.assertEqual(
            self.meta,
            bundle(
                __VIDEO__, __DESIGN__, coordinates, transform,
                order, self.colors, height, timestep
            )
        )

    def test_colors_from_masks(self):
        self.assertEqual(
            self.colors,
            colors_from_masks(masks)
        )

    def test_bundle_readable(self):
        transformed_keys = [
            __coordinates__, __transform__, __order__, __colors__
        ]

        readable = bundle_readable(
            __VIDEO__, __DESIGN__, coordinates, transform,
            order, self.colors, height, timestep
        )
        for key in self.meta:
            if key not in transformed_keys:
                self.assertEqual(self.meta[key], readable[key])
            else:
                pass  # don't care for now

    def test_save(self):
        pass  # skip for now

    def test_save_to_excel(self):
        pass  # todo: does this work outside of Windows?

    def test_load(self):
        pass  # skip for now