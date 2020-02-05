class InteractiveMethod(object):
    """Wraps around a method to provide CLI/GUI interaction with arguments
    """
    pass


class VideoInterface(object):
    """Interface to video files ~ OpenCV
    """
    def __init__(self, video_path):
        pass

    def set_position(self, frame_number=0):
        pass

    def get_frame(self, frame_number=0.5, to_hsv=True, cache=False):
        # If frame_number is an int in [0,1]
        #  frame_number
        #    <- frame_number*len(self.capture.get(cv2.CAP_PROP_FRAME_COUNT))
        # Check cache
        # Get frame from OpenCV capture
        pass


class VideoAnalyzer(VideoInterface):
    """Main video handling class
        * Load frames from video files
        * Load mask files
        * Load/save measurement metadata
    """
    def __init__(self, video_path, svg_path, dt, h, kernel):
        super(VideoAnalyzer, self).__init__(video_path)
        pass

    def check_files(self):
        pass

    def handle_svg(self):
        pass

    def get_frame(self, frame_number=0.5,
                  do_transform=True, to_hsv=True, cache=False):
        super(VideoAnalyzer, self).get_frame(frame_number, to_hsv)
        # transform
        pass

    def get_next_frame(self, to_hsv = True):
        pass

    def get_state_image(self):
        pass


class Transform(object):
    """Handles coordinate transforms.
        Transform objects can point to a parent transform
        -- the transform is applied in sequence!
    """
    pass


class Filter(object):
    """Handles pixel filtering operations
    """
    pass


class HueRangeFilter(Filter):
    """Filters by a range of hues ~ HSV representation
    """
    pass


class Mask(object):
    """Handles masks in the context of a video file
    """
    pass


class guiElement(object):
    """Abstract class for GUI elements
    """
    pass


class guiInteractiveMethod(guiElement):
    """GUI representation of an interactive method
    """
    pass


class guiWindow(object):
    """Abstract class for a GUI window
    """
    pass


class guiTransform(guiWindow):
    """A manual transform selection window
    """
    pass


class guiFilter(guiWindow):
    """A manual filter selection window
    """
    pass


class guiProgress(guiWindow):
    """A progress window
    """
    pass