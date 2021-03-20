from pathlib import Path
from typing import List

from lxml import etree
from lxml.etree import _Element, fromstring

from shapeflow.core import RootException, get_logger
from shapeflow.design.render import save_svg


log = get_logger(__name__)


class DesignFileError(RootException):
    pass


class Layer:
    """Represents a layer within an SVG file
    """
    _root: _Element
    _label: str

    def __init__(self, root: _Element, label: str):
        self._root = root
        self._label = label

    @property
    def label(self):
        return self._label

    def hide(self) -> None:
        """Hide this layer
        """
        self._root.attrib['style'] = 'display:none'

    def show(self) -> None:
        """Show this layer
        """
        self._root.attrib['style'] = 'display:inline'


class Peeler:
    """Renders an SVG file into multiple PNG files layer-per-layer.
    """
    file: Path
    """Path to the SVG file
    """

    G = "{http://www.w3.org/2000/svg}g"
    LABEL = "{http://www.inkscape.org/namespaces/inkscape}label"
    NAMEDVIEW = "{http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd}namedview"
    BG_COLOR = "pagecolor"
    BG_OPACITY = "{http://www.inkscape.org/namespaces/inkscape}pageopacity"

    _header: bytes
    _root: _Element
    _layers: List[Layer]

    def __init__(self, file: Path):
        self.file = file

        try:
            with open(file, 'r') as f:
                svg = bytes(f.read(), encoding='UTF-8')
                self._header = bytes(
                    svg.decode(encoding='UTF-8').split('<svg')[0],
                    encoding='UTF-8'
                )
                self._root = fromstring(svg)
                self._set_background_to_white()
        except Exception as e:
            raise DesignFileError(f"Invalid SVG file: {file} ({e})")

        self._get_layers()

    def peel(self, dpi: int, to_dir: Path) -> None:
        """"Peel" the layers
        """
        log.info(f"Peeling {self.file} @ {dpi} DPI...")

        if to_dir.is_dir():
            for file in to_dir.iterdir():
                file.unlink()
        else:
            to_dir.mkdir()

        for layer in self._layers:
            for hidden in self._layers:
                hidden.hide()
            layer.show()
            self._save(to_dir / f"{layer.label}.png", dpi)

        log.info(f"Done.")

    def _set_background_to_white(self):
        namedview = self._root.find(self.NAMEDVIEW)
        namedview.set(self.BG_COLOR, '#ffffff')
        namedview.set(self.BG_OPACITY, '1.0')

    def _get_layers(self):
        self._layers = []

        for child in self._root.getchildren():
            if child.tag == self.G and self.LABEL in child.attrib:
                if child.attrib[self.LABEL][0] != "_":
                    self._layers.append(Layer(child, child.attrib[self.LABEL]))

    def _as_svg(self) -> bytes:
        return self._header + etree.tostring(self._root)

    def _save(self, to: Path, dpi: int):
        save_svg(self._as_svg(), dpi, to)
