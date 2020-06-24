import unittest

from isimple.maths.images import *
from isimple.maths.colors import *
from isimple.maths.coordinates import *

import numpy as np
import cv2


ckernel_1 = np.array(
        [[1]], dtype=np.uint8) * 255
ckernel_3 = np.array(
    [[0, 1, 0],
     [1, 1, 1],
     [0, 1, 0]], dtype=np.uint8) * 255
ckernel_5 = np.array(
    [[0, 0, 1, 0, 0],
     [0, 1, 1, 1, 0],
     [1, 1, 1, 1, 1],
     [0, 1, 1, 1, 0],
     [0, 0, 1, 0, 0]], dtype=np.uint8) * 255

mask1 = np.array(
    [[1, 1, 0],
     [1, 1, 0],
     [0, 0, 0]], dtype=np.uint8) * 255
mask1_cropped = np.array(
    [[1, 1, ],
     [1, 1, ]], dtype=np.uint8) * 255
ckernel3_mask1 = np.array(
    [[0, 1, ],
     [1, 1, ]], dtype=np.uint8) * 255

mask2 = np.array(
    [[0, 0, 0, 0, 0],
     [0, 1, 1, 0, 0],
     [0, 1, 0, 1, 0],
     [0, 0, 1, 1, 0],
     [0, 0, 0, 0, 0]], dtype=np.uint8) * 255
mask2_cropped = np.array(
    [[1, 1, 0],
     [1, 0, 1],
     [0, 1, 1]], dtype=np.uint8) * 255
ckernel5_mask2 = np.array(
    [[1, 1, 0],
     [1, 0, 1],
     [0, 1, 1]], dtype=np.uint8) * 255


class ckernelTest(unittest.TestCase):
    ckernel_1 = ckernel_1.copy()
    ckernel_3 = ckernel_3.copy()
    ckernel_5 = ckernel_5.copy()

    def test_smallsizes(self):
        for ck1, ck2 in zip(
            [
                ckernel(1),
                ckernel(2),
                ckernel(3),
                ckernel(4),
                ckernel(5),
                ckernel(6),
            ],
            [
                self.ckernel_1,
                self.ckernel_1,
                self.ckernel_3,
                self.ckernel_3,
                self.ckernel_5,
                self.ckernel_5,
            ]
        ):
            self.assertTrue(np.equal(ck1, ck2).all())

    def test_odd_size(self):
        Nr, Nc = ckernel(77).shape
        self.assertEqual(Nr, 77)
        self.assertEqual(Nc, 77)

    def test_even_size(self):
        Nr, Nc = ckernel(168).shape
        self.assertEqual(Nr, 167)
        self.assertEqual(Nc, 167)


class crop_maskTest(unittest.TestCase):
    mask1 = mask1.copy()
    mask1_cropped = mask1_cropped.copy()
    ckernel3_mask1 = ckernel3_mask1.copy()

    mask2 = mask2.copy()
    mask2_cropped = mask2_cropped.copy()
    ckernel5_mask2 = ckernel5_mask2.copy()

    def test_crop_mask1(self):
        # Assert that original mask is unchanged
        self.assertTrue(
            np.equal(
                self.mask1, mask1
            ).all()
        )
        cropped_mask, rectangle, center = crop_mask(self.mask1)

        self.assertTrue(
            np.equal(
                cropped_mask, self.mask1_cropped
            ).all()
        )
        self.assertTrue(
            np.equal(
                rectangle, [0, 2, 0, 2]
            ).all()
        )
        self.assertTrue(
            np.equal(
                center, [0, 0]
            ).all()
        )

        self.assertTrue(  # Mask should be unchanged
            np.equal(
                self.mask1, mask1
            ).all()
        )

    def test_crop_mask2(self):
        cropped_mask, rectangle, center = crop_mask(self.mask2)

        self.assertTrue(
            np.equal(
                cropped_mask, self.mask2_cropped
            ).all()
        )
        self.assertTrue(
            np.equal(
                rectangle, [1, 4, 1, 4]
            ).all()
        )
        self.assertTrue(
            np.equal(
                center, [2, 2]
            ).all()
        )

        self.assertTrue(  # Mask should be unchanged
            np.equal(
                self.mask2, mask2
            ).all()
        )

    def test_apply_mask1(self):
        cropped_mask, rectangle, _ = crop_mask(self.mask1)

        self.assertTrue(
            np.equal(
                mask(ckernel(3), cropped_mask, rectangle),
                self.ckernel3_mask1
            ).all()
        )

        self.assertTrue(  # Mask should be unchanged
            np.equal(
                self.mask1, mask1
            ).all()
        )

    def test_apply_mask2(self):
        """ todo: by this test, for some reason, self.mask2 is changed!
        array([[  0,   0,   0,   0,   0],
               [  0, 255, 255, 255,   0],
               [  0, 255, 255, 255,   0],
               [  0, 255, 255, 255,   0],
               [  0,   0,   0,   0,   0]], dtype=uint8)
        """
        cropped_mask, rectangle, _ = crop_mask(self.mask2)

        self.assertTrue(
            np.equal(
                mask(ckernel(5), cropped_mask, rectangle),
                self.ckernel5_mask2
            ).all()
        )

        self.assertTrue(  # Mask should be unchanged
            np.equal(
                self.mask2, mask2
            ).all()
        )


class area_pixelsumTest(unittest.TestCase):
    def test_zeros(self):
        self.assertEqual(0, area_pixelsum(np.zeros(5)))

    def test_kernel5(self):
        self.assertEqual(13, area_pixelsum(ckernel_5))


class colorTest(unittest.TestCase):
    colors = {
        'rgb': (51, 127, 63),
        'bgr': (63, 127, 51),
        'hsv': (65, int(0.6*255), int(0.5*255))
    }

    def test_coercion(self):
        self.assertEqual(
            RgbColor(0, 255, 150),
            RgbColor(-50, 500, 150)
        )

    def test_addition(self):
        self.assertEqual(
            RgbColor(60,130,70),
            RgbColor(*self.colors['rgb']) + RgbColor(9,3,7)
        )
        self.assertEqual(
            RgbColor(255,255,255),
            RgbColor(*self.colors['rgb']) + RgbColor(255,255,255)
        )
        self.assertEqual(
            RgbColor(0, 0, 0),
            RgbColor(*self.colors['rgb']) - RgbColor(255, 255, 255)
        )

    def test_hue_addition(self):
        self.assertEqual(
            HsvColor(80, 153, 128),
            HsvColor(50, 153, 128) + HsvColor(30, 0, 0)
        )

        self.assertEqual(
            HsvColor(160, 153, 128),
            HsvColor(50, 153, 128) - HsvColor(70, 0, 0)
        )

    def test_conversion(self):
        self.assertEqual(
            RgbColor(*self.colors['rgb']),
            convert(BgrColor(*self.colors['bgr']), RgbColor)
        )
        self.assertEqual(
            HsvColor(*self.colors['hsv']),
            convert(RgbColor(*self.colors['rgb']), HsvColor)
        )


    def test_np_array(self):
        self.assertTrue(
            np.all(np.equal(
                np.array(self.colors['rgb']),
                RgbColor(*self.colors['rgb']).np3d
            ))
        )

    def test_string(self):
        self.assertEqual(
            HsvColor(*self.colors['hsv']),
            HsvColor.from_str(str(HsvColor(*self.colors['hsv'])))
        )


class coordinateTest(unittest.TestCase):
    co1 = ShapeCoo(x=0.101, y=0.199, shape=(150,250))
    co2 = ShapeCoo(x=0.301, y=0.299, shape=(300,300))

    def test_equality(self):
        self.assertEqual(
            self.co1,
            ShapeCoo(x=0.101, y=0.199, shape=(150,250))
        )
        self.assertEqual(
            self.co2,
            ShapeCoo(x=0.301, y=0.299, shape=(300, 300))
        )
        self.assertNotEqual(
            self.co2,
            ShapeCoo(x=0.6, y=0.299, shape=(300,300))
        )
        self.assertNotEqual(
            self.co2,
            ShapeCoo(x=0.301, y=0.6, shape=(300, 300))
        )
        self.assertNotEqual(
            self.co2,
            ShapeCoo(x=0.301, y=0.299, shape=(301, 300))
        )
        self.assertNotEqual(
            self.co2,
            ShapeCoo(x=0.301, y=0.299, shape=(300, 299))
        )

    def test_abs(self):
        self.assertEqual(
            (29.85, 25.25),
            self.co1.abs
        )
        self.assertEqual(
            (89.7, 90.3),
            self.co2.abs
        )

    def test_idx(self):
        self.assertEqual(
            (30, 25),
            self.co1.idx
        )
        self.assertEqual(
            (90, 90),
            self.co2.idx
        )

    def test_value(self):
        image1 = np.random.random(self.co1.shape)
        image2 = np.random.random(self.co2.shape)

        self.assertEqual(
            image1[30, 25],
            self.co1.value(image1)
        )
        self.assertEqual(
            image2[90, 90],
            self.co2.value(image2)
        )

        self.assertRaises(
            AssertionError,
            self.co1.value, image2
        )

        self.assertRaises(
            AssertionError,
            self.co2.value, image1
        )

    # todo: do some basic translation / scale / rotation transforms
    #       * should be relatively tame; cv2 should be able to transform
    #           arrays as images in a way that all pixels are still ~ accessible
    #       * compare to coordinate transformation by hand
    #       * compare sampled values
    #           ~ transformed image & transformed coordinate
    #             vs. original image & original coordinate


if __name__ == '__main__':
    unittest.main()
