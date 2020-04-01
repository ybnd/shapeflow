import numpy as np
import cv2

from typing import Tuple, Union

from isimple.maths.coordinates import Coo


def ckernel(size: int) -> np.ndarray:
    """Circular filter kernel
    """
    if not size % 2:
        # size must be odd
        size = size - 1
    index = int(size / 2)

    y, x = np.ogrid[-index:size - index, -index:size - index]  # todo: what's this?
    r = int(size / 2)
    mask = x * x + y * y <= r * r  # disc formula
    array = np.zeros([size, size], dtype=np.uint8)
    array[mask] = 255
    return array


def overlay(frame: np.ndarray, overlay: np.ndarray, alpha: float = 0.5) -> np.ndarray:
    """Overlay `frame` image with `overlay` image.
        * Both images should be in the BGR color space
    """
    # https://stackoverflow.com/questions/54249728/
    return cv2.addWeighted(
        overlay, alpha,
        frame, 1 - alpha,
        gamma=0, dst=frame
    )


def crop_mask(mask: np.ndarray) -> Tuple[np.ndarray, np.ndarray, Tuple[int, int]]:
    """Crop a binary mask image array to its minimal (rectangular) size
        to exclude unnecessary regions
    """

    nz = np.nonzero(mask)
    row_0 = nz[0].min()     # todo: document, it's confusing!
    row_1 = nz[0].max()+1
    col_0 = nz[1].min()
    col_1 = nz[1].max()+1
    cropped_mask = mask[row_0:row_1, col_0:col_1].copy()

    return cropped_mask, \
        np.array([row_0, row_1, col_0, col_1]), \
        (int((row_0+row_1-1)/2), int((col_0+col_1-1)/2))


def rect_contains(rect: np.ndarray, point: Coo) -> bool:
    """Check whether `point` is in `rect`
    :param rect: an 'array rectangle': [first_row, last_row, first_column, last_column]
    :param point: a coordinate as (row, column)
    :return:
    """
    return (rect[0] <= point.abs[0] <= rect[1]) \
           and (rect[2] <= point.abs[1] <= rect[3])


def mask(image: np.ndarray, mask: np.ndarray, rect: np.ndarray):
    cropped_image = image[rect[0]:rect[1], rect[2]:rect[3]].copy()
    return cv2.bitwise_and(cropped_image, mask)


def area_pixelsum(image):
    """Calculate area in px^2 by summing pixels

    :param image:   Binary input image (numpy array).
                    Should already be masked and filtered.
    :return:        Area as # of pixels
    """
    if image is not None:
        return np.sum(image > 1)


def to_mask(image: np.ndarray, kernel: np.ndarray = ckernel(7)) -> np.ndarray:
    """Convert a .png image to a binary mask
    """

    # Convert to grayscale
    image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    # Threshold to binary
    ret, image = cv2.threshold(image, 254, 255, cv2.THRESH_BINARY)
    # Expand binary region to deal with
    #  'under-thresholding' due to high setting (254/255)
    image = cv2.morphologyEx(image, cv2.MORPH_OPEN, kernel)

    # The binary threshold does not always map the same binary value
    # to the center of the mask (should be the darker tone)
    # To circumvent this, we assume that the outer edge is
    # not included in the mask (should be ok in normal cases)

    # We want to end up with the mask as 255, the background as 0

    # Apparently that's not it, do the arithmetic
    #  in float & convert to uint8 afterwards!

    if image[0, 0] == 255:  # todo: we're hardcoding pixel 0,0 as background here, this is not ideal!
        # Do the arithmetic in float & convert to uint8 afterwards!
        return np.array(
            np.abs(
                np.subtract(
                    255, np.array(
                        image, dtype=np.float
                    )
                )
            ), dtype=np.uint8
        )
    else:
        return image

