import unittest

from isimple.utility.images import *
import numpy as np


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





if __name__ == '__main__':
    unittest.main()
