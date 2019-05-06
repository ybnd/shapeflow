import numpy as np


def area_pixelsum(image):
    """
    Count non-zero pixels in image

    :param image:   Binary input image (numpy array). Should already be masked and filtered.
    :return:        Area as # of pixels
    """
    return np.sum(image > 1)


def filter_hsv_interval_fixed(color):
    """
    Get filtering interval based on selected color value.

    :param color:   HSV Color
    :return:        from, to: lower and upper bound of the filter (in HSV)
    """
    pass
