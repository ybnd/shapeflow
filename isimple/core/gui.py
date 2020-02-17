from typing import List

from isimple.core.common import Manager, EndpointRegistry


gui = EndpointRegistry()


class guiElement(object):
    """Abstract class for GUI elements
    """
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
