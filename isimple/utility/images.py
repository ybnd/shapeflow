import numpy as np
import cv2


def ckernel(size: int) -> np.ndarray:
    """Circular filter kernel
    """
    if not size % 2: size = size - 1
    index = int(size / 2)

    y, x = np.ogrid[-index:size - index, -index:size - index]
    r = int(size / 2)
    mask = x * x + y * y <= r * r
    array = np.zeros([size, size], dtype=np.uint8)
    array[mask] = 255
    return array


def crop_mask(mask: np.ndarray) -> (np.ndarray, np.ndarray, np.ndarray):
    """Crop a binary mask image to its minimal size
        (to exclude unnecessary regions)
    """

    nz = np.nonzero(mask)
    row_0 = nz[0].min()
    row_1 = nz[0].max()+1
    col_0 = nz[1].min()
    col_1 = nz[1].max()+1
    cropped_mask = mask[row_0:row_1, col_0:col_1].copy()

    return cropped_mask, \
        np.array([row_0, row_1, col_0, col_1]), \
        (int((row_0+row_1-1)/2), int((col_0+col_1-1)/2))


def mask(image: np.ndarray, mask: np.ndarray, rect: np.ndarray):
    cropped_image = image[rect[0]:rect[1], rect[2]:rect[3]].copy()
    return cv2.bitwise_and(cropped_image, mask)