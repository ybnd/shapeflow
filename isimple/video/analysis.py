import numpy as np
import cv2


def area_pixelsum(_, image):
    """
    Count non-zero pixels in image

    :param image:   Binary input image (numpy array). Should already be masked and filtered.
    :return:        Area as # of pixels
    """
    if image is not None:
        return np.sum(image > 1)


def filter_hsv_interval_fixed(color):
    """
    Get filtering interval based on selected color value.

    :param color:   HSV Color
    :return:        from, to: lower and upper bound of the filter (in HSV)
    """
    if color is not None:
        pass


def to_mask(_, image: np.ndarray, kernel: np.ndarray) -> np.ndarray:
    """ Convert a .png image to a binary mask """
    image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)  # Convert to grayscale
    ret, image = cv2.threshold(image, 254, 255, cv2.THRESH_BINARY)  # Threshold to binary
    image = cv2.morphologyEx(image, cv2.MORPH_OPEN, kernel)  # Expand binary region to deal with 'under-thresholding' due to high setting (254/255)

    # The binary threshold does not always map the same binary value to the center of the mask (should be the darker tone)
    # To circumvent this, we assume that the outer edge is not included in the mask (should be ok in normal cases)
    #   We want to end up with the mask as 255, the background as 0

    # Apparently that's not it, do the arithmetic in float & convert to uint8 afterwards!

    if image[0,0] == 255:
        return np.array(np.abs(np.subtract(255, np.array(image, dtype=np.float))), dtype=np.uint8)
    else:
        return image
