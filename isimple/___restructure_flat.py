from diskcache import Cache
import cv2
import os
import time
import logging
import traceback


__CACHE_DIRECTORY__ = '.cache'
__CACHE_SIZE_LIMIT__ = 2 ** 32

logging.basicConfig(
    filename='.log', level=logging.DEBUG
)


class VideoInterface(object):
    """Interface to video files ~ OpenCV
    """

    def __init__(self, video_path):
        self.path = video_path
        self.name = video_path.split('\\')[-1].split('.png')[0]
        self._cache = None

        self._capture = cv2.VideoCapture(
            os.path.join(os.getcwd(), self.path)
        )  # todo: handle failure to open capture

        self.Nframes = int(self._capture.get(cv2.CAP_PROP_FRAME_COUNT))
        self.fps = self._capture.get(cv2.CAP_PROP_FPS)
        self.frame_number = None

    def _get_key(self, frame_number, to_hsv) -> int:
        return hash(f"{self.path} {frame_number} {to_hsv}")

    def _set_position(self, frame_number: int):
        self._capture.set(cv2.CAP_PROP_POS_FRAMES, frame_number)
        self._get_position()

    def _get_position(self) -> int:
        self.frame_number = self._capture.get(cv2.CAP_PROP_POS_FRAMES)
        return self.frame_number

    def get_frame(self, frame_number: int = None,
                  to_hsv: bool = True, from_cache = False):
        key = self._get_key(frame_number, to_hsv)
        # Check cache
        if key in self._cache:
            # Get frame from cache
            frame = self._cache.get(key)

            while isinstance(frame, str) and frame == 'in progress':
                # Some other thread is currently reading the same frame
                # Wait a bit and try to get from cache again
                time.sleep(0.01)  # todo: DiskCache-level events?
                frame = self._cache.get(key)

            return frame
        elif not from_cache:
            # Deposit a temporary entry into the cache
            self._cache.set(key, 'in progress')

            # Get frame from OpenCV capture
            if frame_number is None:
                frame_number = int(self.Nframes / 2)

            self._set_position(frame_number)
            ret, frame = self._capture.read()

            if ret:
                if to_hsv:
                    frame = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

                self._cache.set(key, frame)
                return frame
            else:
                return None  # todo: what do when no frame? cases?

    def __enter__(self):
        self._cache = Cache(
            directory=__CACHE_DIRECTORY__,
            size_limit=__CACHE_SIZE_LIMIT__,
        )
        return self

    def __exit__(self, exc_type, exc_value, tb):
        self._cache.close()
        if exc_type is not None:
            return False
        else:
            return True

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
                  do_transform=True, to_hsv=True):
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