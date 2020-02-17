from typing import List, Callable

from isimple.core.common import Manager
from isimple.endpoints import GuiEndpoints


gui = GuiEndpoints()


class guiElement(object):
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


class guiManager(Manager):
    _instances: List[guiElement]
    _instance_class = guiElement

class SetupWindow(guiWindow):
    @gui.expose(gui.open_setupwindow)  # todo: ... some way to combine gui and geep into one thing?
    def open(self, configure_callback: Callable) -> None:   # todo: can add beep.configure.signature as a type hint?
        pass


class TransformWindow(guiWindow):
    @gui.expose(gui.open_transformwindow)
    def open(self, estimate_callback: Callable) -> None:
        pass


class FilterWindow(guiWindow):
    @gui.expose(gui.open_filterwindow)
    def open(self, set_callback: Callable, seek_callback: Callable) -> None:
        pass


class ProgressWindow(guiWindow):
    @gui.expose(gui.open_progresswindow)  # todo: this thing should provide its own callbacks tho
    def open(self) -> None:
        pass

    @gui.expose(gui.update_progresswindow)
    def update(self) -> None:
        pass


class VideoAnalyzerGui(guiManager):
    _backend: Manager  # todo: good idea to have these two in "direct contact"?

    def __init__(self, backend: Manager):
        self._backend = backend
