from typing import List, Callable
import abc

import numpy as np

from isimple.core.common import Manager, Endpoint
from isimple.endpoints import GuiEndpoints
from isimple.endpoints import BackendEndpoints as backend


gui = GuiEndpoints()


class guiElement(abc.ABC):
    """Abstract class for GUI elements
    """

    def __init__(self):
        pass

    def build(self):
        pass

class guiPane(guiElement):
    """Abstract class for a GUI pane
    """
    pass

class guiWindow(guiElement):
    """Abstract class for a GUI window
    """
    def open(self):
        pass

    def close(self):
        pass


class SetupWindow(guiWindow):
    set_video_path_callback = backend.get_raw_frame.signature
    set_design_path_callback = backend.get_raw_frame.signature
    configure_callback = backend.get_raw_frame.signature


class TransformWindow(guiWindow):
    """Allows the user to set up a transform interactively
            * Callbacks:
                - Get the raw and transformed frame at a certain frame number (scrollable)
                - Estimate the transform for a set of coordinates
        """
    get_raw_frame_callback = backend.get_raw_frame.signature
    estimate_transform_callback = backend.get_raw_frame.signature
    get_transformed_frame_callback = backend.get_raw_frame.signature
    get_transformed_overlaid_frame_callback = backend.get_raw_frame.signature
    get_inverse_transformed_overlay_callback = backend.get_raw_frame.signature


class FilterWindow(guiWindow):
    """Allows the user to set up a filter interactively
        * Interaction:
            - Scroll through the video to find the liquid of interest,
              click on it and set the filter according to the selected pixel
            - todo: extra GUI elements for more control over filter parameters
            - todo: would be great to change the filter *type* dynamically; in that
                    case the gui Manager would have to be involved in order to
                    update the FilterWindow's callbacks...
                    Otherwise: filter implementations wrapped by Filter, not
                    inheriting from Filter
        * Callbacks:
            - Get the masked / masked & filtered frame at a certain frame number (scrollable)
            - Set the filter
            - todo:
    """
    get_masked_frame_callable = backend.get_raw_frame.signature
    set_filter_callback = backend.get_raw_frame.signature
    get_filtered_masked_frame_callable = backend.get_raw_frame.signature


class ProgressWindow(guiWindow):
    """Shows the progress of an analysis.
        * No callbacks; not interactive, so the backend pushes to the GUI instead
    """
    @gui.expose(gui.update_progresswindow)
    def update(self, values: list, state: np.ndarray) -> None:
        pass


class VideoAnalyzerGui(Manager):  # todo: good idea to have these two in "direct contact"?
    windows: List[guiWindow]

    _instances: List[guiElement]
    _instance_class = guiElement

    _backend: Manager

    def __init__(self, backend: Manager):
        self._backend = backend

    @gui.expose(gui.open_setupwindow)
    def open_setupwindow(self) -> None:
        sw = SetupWindow()

        sw.set_video_path_callback = self._backend.get(backend.set_video_path)
        sw.set_design_path_callback = self._backend.get(backend.set_design_path)
        sw.configure_callback = self._backend.get(backend.configure)

        self.open_window(sw)

    @gui.expose(gui.open_transformwindow)
    def open_transformwindow(self) -> None:
        tw = TransformWindow()

        tw.get_raw_frame_callback = self._backend.get(backend.get_raw_frame)
        tw.estimate_transform_callback = self._backend.get(backend.estimate_transform)
        tw.get_transformed_frame_callback = self._backend.get(backend.get_frame)
        tw.get_transformed_overlaid_frame_callback = self._backend.get(backend.get_overlaid_frame)
        tw.get_inverse_transformed_overlay_callback = self._backend.get(backend.get_inverse_transformed_overlay)

        self.open_window(tw)

    @gui.expose(gui.open_filterwindow)
    def open_filterwindow(self, index: int) -> None:
        fw = FilterWindow()

        fw.get_masked_frame_callable = self._backend.get(backend.get_masked_frame, index)
        fw.get_filtered_masked_frame_callable = self._backend.get(backend.get_filtered_masked_frame, index)

        self.open_window(fw)

    @gui.expose(gui.open_progresswindow)
    def open_progresswindow(self) -> None:
        pw = ProgressWindow()

        self.open_window(pw)

    def open_window(self, window: guiWindow):
        self.windows.append(window)

    def close_window(self, index: int):
        window = self.windows.pop(index)
        window.close()

    def close_all_windows(self):
        for window in self.windows:
            window.close()
