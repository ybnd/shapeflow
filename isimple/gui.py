from typing import List

from isimple.core.gui import gui, guiWindow
from isimple.core.endpoints import beep, geep


class SetupWindow(guiWindow):
    @gui.expose(geep.open_setupwindow)  # todo: ... some way to combine gui and geep into one thing?
    def open(self, configure_callback):   # todo: can add beep.configure.signature as a type hint?
        pass


class TransformWindow(guiWindow):
    @gui.expose(geep.open_transformwindow)
    def open(self, estimate_callback):
        pass


class FilterWindow(guiWindow):
    @gui.expose(geep.open_filterwindow)
    def open(self, set_callback, seek_callback):
        pass


class ProgressWindow(guiWindow):
    @gui.expose(geep.open_progresswindow)  # todo: this thing should provide its own callbacks tho
    def open(self):
        pass

    @gui.expose(geep.update_progresswindow)
    def update(self):
        pass
