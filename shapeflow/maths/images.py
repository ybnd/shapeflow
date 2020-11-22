"""Some basic tools for working with images.
"""

import numpy as np
import cv2

from typing import Tuple, Optional

from shapeflow.maths.coordinates import ShapeCoo

def ckernel(size: int) -> np.ndarray:
    """Circular/disk kernel.

    Parameters
    ----------
    size: int
        The size or diameter of the kernel. Should be odd; if an even value is
        supplied, it will be decremented.

    Returns
    -------
    np.ndarray
        A disk kernel as a ``numpy`` array
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
    Both images should be in the BGR color space.
    """
    # https://stackoverflow.com/questions/54249728/
    return cv2.addWeighted(
        overlay, alpha,
        frame, 1 - alpha,
        gamma=0, dst=frame
    )


def crop_mask(mask: np.ndarray) -> Tuple[np.ndarray, np.ndarray, Tuple[int, int]]:
    """Crop a binary mask image array to its minimal (rectangular) size
    to exclude unnecessary regions.
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


def rect_contains(rect: np.ndarray, point: ShapeCoo) -> bool:
    """Check whether a point is contained in a rectangle.

    Parameters
    ----------
    rect: np.ndarray
        An 'array rectangle': [first_row, last_row, first_column, last_column]
    point: ShapeCoo
        A point on a 2D image with known size

    Returns
    -------
    bool
        Whether the point is contained in the rectangle or not.
    """
    """Check whether `point` is in `rect`
    :param rect: an 'array rectangle': [first_row, last_row, first_column, last_column]
    :param point: a coordinate as (row, column)
    :return:
    """
    return (rect[0] <= point.abs[0] <= rect[1]) \
           and (rect[2] <= point.abs[1] <= rect[3])


def mask(image: np.ndarray, mask: np.ndarray, rect: np.ndarray) -> np.ndarray:
    """Mask and crop off a part of an image.

    Parameters
    ----------
    image: np.ndarray
        The original image
    mask: np.ndarray
        The mask. Should be an ``OpenCV``-compatible
        binary image, with ``False -> 0`` and ``True -> 255``
    rect: np.ndarray
        An 'array rectangle': [first_row, last_row, first_column, last_column].
        Should correspond to the position of the mask in the original image.

    Returns
    -------
    np.ndarray
        The image cropped by ``rect`` and masked by ``mask``
    """
    cropped_image = image[rect[0]:rect[1], rect[2]:rect[3]].copy()
    return cv2.bitwise_and(cropped_image, mask)


def area_pixelsum(image: Optional[np.ndarray]) -> Optional[int]:
    """Get the total number of ``True`` pixels in a binary image.

    Parameters
    ----------
    image: np.ndarray
        An ``OpenCV``-compatible binary image, with
        ``False -> 0`` and ``True -> 255``.

    Returns
    -------
    int
        The number of ``255`` pixels in the image
    """
    if image is not None:
        return int(np.sum(image > 1))
    else:
        return None


def to_mask(image: np.ndarray, kernel: np.ndarray = None) -> np.ndarray:
    """Convert a PNG image to a binary mask array.

    Parameters
    ----------
    image: np.ndarray
        A ``numpy`` array representing a full-color PNG image
        without transparency
    kernel: Optional[np.ndarray]
        A smoothing kernel.
        If set to ``None``, defaults to a
        :func:`~shapeflow.maths.images.ckernel` of size 7.


    Returns
    -------

    """
    if kernel is None:
        kernel = ckernel(7)

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

