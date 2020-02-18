from typing import List, Dict
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
    def open(self):  # todo: should check if all callbacks have been provided
        pass

    def close(self):
        pass


class SetupWindow(guiWindow):
    get_arguments_callback = backend.get_arguments.signature
    set_video_path_callback = backend.get_raw_frame.signature
    set_design_path_callback = backend.get_raw_frame.signature
    configure_callback = backend.get_raw_frame.signature

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
    get_total_frames_callback = backend.get_total_frames.signature
    get_overlay_callback = backend.get_overlaid_frame.signature
    overlay_frame_callback = backend.get_overlaid_frame.signature
    get_raw_frame_callback = backend.get_raw_frame.signature
    transform_callback = backend.transform.signature
    estimate_transform_callback = backend.get_raw_frame.signature
    get_transformed_frame_callback = backend.get_raw_frame.signature
    get_transformed_overlaid_frame_callback = backend.get_raw_frame.signature
    get_inverse_transformed_overlay_callback = backend.get_raw_frame.signature

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
    get_total_frames_callback = backend.get_total_frames.signature
    get_frame_callback = backend.get_frame.signature
    mask_callback = backend.mask.signature
    get_filter_callback = backend.get_filter_parameters.signature
    set_filter_callback = backend.set_filter_parameters.signature
    filter_callback = backend.filter.signature

    def __init__(self):
        super().__init__()

    def open(self):
        og.gui.MaskFilterWindow(self)


class ProgressWindow(guiWindow):
    """Shows the progress of an analysis.
        * No callbacks; not interactive, so the backend pushes to the GUI instead
    """

    get_name_callback = backend.get_name.signature
    get_colors_callback = backend.get_colors.signature
    get_frame_callback = backend.get_frame.signature
    get_raw_frame_callback = backend.get_raw_frame.signature
    get_total_frames_callback = backend.get_total_frames.signature
    get_fps_callback = backend.get_fps.signature
    get_h_callback = backend.get_h.signature
    get_dpi_callback = backend.get_dpi.signature
    get_mask_names = backend.get_mask_names.signature

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

        for c in [SetupWindow, TransformWindow, FilterWindow, ProgressWindow]:
            self.add_window(c, c())

        self._gather_instances()

    @gui.expose(gui.open_setupwindow)
    def open_setupwindow(self) -> None:  # todo: probably a bad idea to give out references to the actual windows; maybe give index or key instead?
        sw = self.windows[SetupWindow]   # todo: this setup process can be generalized: open a window of class <C>: get from dict, assert, add all requested callbacks, open
        assert isinstance(sw, SetupWindow)

        sw.get_arguments_callback = self._backend.get(backend.get_arguments)
        sw.set_video_path_callback = self._backend.get(backend.set_video_path)
        sw.set_design_path_callback = self._backend.get(backend.set_design_path)
        sw.configure_callback = self._backend.get(backend.set_config)

        self.open_window(sw)

    @gui.expose(gui.open_transformwindow)
    def open_transformwindow(self) -> None:
        tw = self.windows[TransformWindow]
        assert isinstance(tw, TransformWindow)

        tw.get_total_frames_callback = self._backend.get(backend.get_total_frames)
        tw.get_overlay_callback = self._backend.get(backend.get_overlay)
        tw.overlay_frame_callback = self._backend.get(backend.overlay_frame)
        tw.get_raw_frame_callback = self._backend.get(backend.get_raw_frame)
        tw.transform_callback = self._backend.get(backend.transform)
        tw.estimate_transform_callback = self._backend.get(backend.estimate_transform)
        tw.get_transformed_frame_callback = self._backend.get(backend.get_frame)
        tw.get_transformed_overlaid_frame_callback = self._backend.get(backend.get_overlaid_frame)
        tw.get_inverse_transformed_overlay_callback = self._backend.get(backend.get_inverse_transformed_overlay)

        self.open_window(tw)

    @gui.expose(gui.open_filterwindow)
    def open_filterwindow(self, index: int) -> None:
        fw = self.windows[FilterWindow]
        assert isinstance(fw, FilterWindow)

        fw.get_total_frames_callback = self._backend.get(backend.get_total_frames)  # todo: some kind of mechanism to make it ok to only write the thing once...
        fw.get_frame_callback = self._backend.get(backend.get_frame)
        fw.mask_callback = self._backend.get(backend.mask, index)
        fw.filter_callback = self._backend.get(backend.filter, index)
        fw.set_filter_callback = self._backend.get(backend.set_filter_parameters, index)
        fw.get_filter_callback = self._backend.get(backend.get_filter_parameters, index)

        self.open_window(fw)

    @gui.expose(gui.open_progresswindow)
    def open_progresswindow(self) -> None:
        pw = self.windows[ProgressWindow]
        assert isinstance(pw, ProgressWindow)

        pw.get_name_callback = self._backend.get(backend.get_name)
        pw.get_colors_callback = self._backend.get(backend.get_colors)
        pw.get_raw_frame_callback = self._backend.get(backend.get_raw_frame)
        pw.get_frame_callback = self._backend.get(backend.get_frame)
        pw.get_total_frames_callback = self._backend.get(backend.get_total_frames)
        pw.get_fps_callback = self._backend.get(backend.get_fps)
        pw.get_h_callback = self._backend.get(backend.get_h)
        pw.get_dpi_callback = self._backend.get(backend.get_dpi)
        pw.get_mask_names = self._backend.get(backend.get_mask_names)

        self.open_window(pw)

    def add_window(self, key: type, window: guiWindow):
        self.windows[key] = window


    def open_window(self, window: guiWindow):
        self.open_windows.append(window)
        window.open()

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

