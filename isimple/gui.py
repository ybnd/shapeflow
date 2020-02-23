from typing import List, Dict, Type, Callable
import abc
import time

import numpy as np

from isimple.core.common import Manager, Endpoint
from isimple.endpoints import GuiEndpoints
from isimple.endpoints import BackendEndpoints as backend

import og.gui


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
    _endpoints: List[Endpoint]

    def __init__(self):
        super().__init__()

    def open(self):  # todo: should check if all callbacks have been provided
        pass

    def close(self):
        pass


class SetupWindow(guiWindow):
    _endpoints = [
        backend.get_config,
        backend.set_config,
    ]

    def __init__(self):  # todo: should limit configuration get/set to backend; metadata saving should be done from there too.
        super().__init__()

    def open(self):
        og.gui.FileSelectWindow(self)


class TransformWindow(guiWindow):
    """Allows the user to set up a transform interactively
            * Callbacks:
                - Get the raw and transformed frame at a certain frame number (scrollable)
                - Estimate the transform for a set of coordinates
        """
    _endpoints = [
        backend.get_total_frames,
        backend.get_overlay,
        backend.overlay_frame,
        backend.get_raw_frame,
        backend.transform,
        backend.estimate_transform,
        backend.get_frame,
        backend.get_overlaid_frame,
        backend.get_inverse_transformed_overlay,
    ]

    def __init__(self):
        super().__init__()

    def open(self):
        og.gui.OverlayAlignWindow(self)


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
    """
    _endpoints = [
        backend.get_total_frames,
        backend.get_frame,
        backend.mask,
        backend.get_filter_parameters,
        backend.set_filter_parameters,
        backend.filter,
    ]

    def __init__(self):
        super().__init__()

    def open(self):
        og.gui.MaskFilterWindow(self)


class ProgressWindow(guiWindow):
    """Shows the progress of an analysis.
        * No callbacks; not interactive, so the backend pushes to the GUI instead
    """
    _endpoints = [
        backend.get_name,
        backend.get_colors,
        backend.get_frame,
        backend.get_raw_frame,
        backend.get_total_frames,
        backend.get_fps,
        backend.get_h,
        backend.get_dpi,
        backend.get_mask_names,
    ]

    def __init__(self):
        super().__init__()

    def open(self):
        self.pw = og.gui.ProgressWindow(self)

    @gui.expose(gui.update_progresswindow)
    def update(self, time: float, values: list, state: np.ndarray, frame: np.ndarray) -> None:
        self.pw.update_window(time, values, state, frame)


class VideoAnalyzerGui(Manager, guiElement):  # todo: find a different name
    windows: Dict[type, guiWindow]
    open_windows: List[guiWindow]

    _instances: List[guiElement]
    _instance_class = guiElement

    _backend: Manager
    _endpoints: GuiEndpoints = gui

    def __init__(self, backend: Manager):
        super().__init__()

        self.windows = {}
        self.open_windows = []

        self._backend = backend
        self._backend.connect(self)

        for c in [SetupWindow, TransformWindow, FilterWindow, ProgressWindow]:  # todo: cleaner way to define this, maybe as a _window_classes class attribute?
            self.add_window(c)

        self._gather_instances()

    @gui.expose(gui.open_setupwindow)
    def open_setupwindow(self) -> None:  # todo: probably a bad idea to give out references to the actual windows; maybe give index or key instead?
        self.open_window(SetupWindow)

    @gui.expose(gui.open_transformwindow)
    def open_transformwindow(self) -> None:
        self.open_window(TransformWindow)

    @gui.expose(gui.open_filterwindow)
    def open_filterwindow(self, index: int) -> None:
        self.open_window(FilterWindow, index)

    @gui.expose(gui.open_progresswindow)
    def open_progresswindow(self) -> None:
        self.open_window(ProgressWindow)

    def add_window(self, window_type: Type[guiWindow]):
        self.windows[window_type] = window_type()


    def open_window(self, window_type: Type[guiWindow], index: int = None):
        w = self.windows[window_type]

        if isinstance(w, list):
            if index is None:
                index = 0
            w = w[index]

        self.open_windows.append(w)

        for endpoint in w._endpoints:
            setattr(w, endpoint._name, self._backend.get(endpoint, index))

        w.open()

    def close_window(self, index: int):
        window = self.open_windows.pop(index)
        window.close()

    def wait_on_close(self, window):  # todo: windows should run in separate threads
        # todo: check that window is in self.windows
        while window.is_open:  # todo: wrap Thread.join() instead
            time.sleep(0.05)

    def close_all_windows(self):
        if hasattr(self, 'windows'):
            for window in self.open_windows:
                window.close()

            self.open_windows = []

