"""Adapted from https://github.com/ybnd/OnionSVG
"""

from typing import List, Union
from pathlib import Path

from lxml import etree
from lxml.etree import _Element, fromstring
from wand.color import Color
from wand.image import Image

from shapeflow import get_logger
from shapeflow.core import RootException


log = get_logger(__name__)


class SvgError(RootException):
    pass


def check_svg(file: Union[Path, str]) -> None:
    """Check whether file is a valid SVG file.

    Parameters
    ----------
    file: Path
        Any file

    Raises
    ------
    SvgError
        If the file can't be read or parsed
    """
    try:
        with open(file, 'r') as f:
            fromstring(
                bytes(f.read(), encoding='UTF-8')
            )
    except Exception as e:
        raise SvgError(f"Invalid SVG file: {file} ({e})")


def peel(file: Union[Path, str], dpi: int, dir: Union[Path, str]) -> None:
    """Render an SVG file layer per layer

    Parameters
    ----------
    file
    dpi
    dir

    Returns
    -------

    """
    if isinstance(file, str):
        file = Path(file)
    if isinstance(dir, str):
        dir = Path(dir)

    Peeler(file).peel(dpi, dir)


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
    background: Color = Color('white')
    """The background color to use for each render (white).
    The background color of the original SVG file is ignored. Moreover, it's no
    longer required to include a "hardcoded" background layer.
    Layers labelled with `_*` are ignored for backwards compatibility with 
    legacy design files.
    """

    G = "{http://www.w3.org/2000/svg}g"
    LABEL = "{http://www.inkscape.org/namespaces/inkscape}label"

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
        except Exception as e:
            raise SvgError(f"Invalid SVG file: {file} ({e})")

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

    def _get_layers(self):
        self._layers = []

        for child in self._root.getchildren():
            if child.tag == self.G and self.LABEL in child.attrib:
                if child.attrib[self.LABEL][0] != "_":
                    self._layers.append(Layer(child, child.attrib[self.LABEL]))

    def _as_svg(self) -> bytes:
        return self._header + etree.tostring(self._root)

    def _save(self, to: Path, dpi: int):
        with open(to, "wb") as f:
            with Image() as image:
                image.read(
                    blob=self._as_svg(),
                    background=self.background,
                    resolution=dpi,
                )
                f.write(image.make_blob("png32"))

        log.debug(f"Rendered {to}")
