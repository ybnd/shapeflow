import numpy as np


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
    row_1 = nz[0].max()
    col_0 = nz[1].min()
    col_1 = nz[1].max()
    cropped_mask = mask[row_0:row_1, col_0:col_1]

    return cropped_mask, \
        np.array([row_0, row_1, col_0, col_1]), \
        ((row_0+row_1)/2, (col_0+col_1)/2)
