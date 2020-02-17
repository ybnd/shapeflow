from typing import List

from isimple.core.common import Manager

class guiElement(object):
    """Abstract class for GUI elements
    """
    pass


class guiPane(guiElement):
    """Abstract class for a GUI pane
    """
    pass


class guiWindow(guiElement):
    """Abstract class for a GUI window
    """
    pass


class guiManager(Manager):
    _instances: List[guiElement]
    _instance_class = guiElement