import abc
import os
from pathlib import Path, WindowsPath
from subprocess import check_call, CalledProcessError
from tempfile import NamedTemporaryFile
from typing import Union, Any, List, Type, Optional

from shapeflow.core import RootException, get_logger


log = get_logger(__name__)


Reason = Optional[Union[Exception, str]]


class RendererError(RootException):
    pass


class Renderer(abc.ABC):
    """Renders SVG (as an XML string) to a PNG image.
    Multiple implementations are provided as a fallback for Windows systems
    where cairo may be unavailable.

    Transparency is handled after importing PNG ~ OpenCV; SVGs are rendered
    with a white background.
    The background color of the original SVG file is ignored. Moreover, it's no
    longer required to include a "hardcoded" background layer.
    Layers labelled with `_*` are ignored for backwards compatibility with
    legacy design files.
    """

    _works: bool
    """Renderer implementations should import their dependencies on __init__.
    If the import is successful, they should set ``_works = True`` to mark that
    this renderer can function properly.
    """
    _reason: Reason
    """The reason why this renderer doesn't work
    """

    def save(self, svg: bytes, dpi: int, to: Path) -> None:
        """Save an SVG string to a PNG image.
        Checks whether this renderer works on the current system before trying.

        Parameters
        ----------
        svg: str
            An SVG image as an XML string
        dpi: int
            The DPI (details per inch) to render the SVG at
        to: Path
            The file to save to
        """
        self._ensure()
        self._save(svg, dpi, to)

    def _ensure(self) -> None:
        """Checks whether this renderer can be used.
        If not, an exception will be raised.

        Raises
        ------
        RendererError
            if this renderer can't be used on the current system
        """
        if not self._works:
            raise RendererError(
                f"can't use {self.__class__.__name__} - {self._reason}"
            )

    def _confirm(self, works: bool, reason: Reason = None) -> None:
        self._works = works
        self._reason = reason

    @abc.abstractmethod
    def _save(self, svg: bytes, dpi: int, to: Path) -> None:
        raise NotImplementedError

    @property
    def works(self) -> bool:
        return self._works


class CairoRenderer(Renderer):
    """First-choice renderer: fastest, cleanest interface.

    Requires the Python package ``cairosvg`` to be installed,
    which in turn depends on ``cairo``.

    Installing ``cairo``

    Installing ``cairosvg``
    """

    cairosvg: Any
    DEFAULT_DPI: int = 96
    WHITE: str = "#ffffff"

    def __init__(self):
        try:
            import cairosvg
            self.cairosvg = cairosvg
            self._confirm(True)
        except Exception as e:
            self._confirm(False, e)

    def _save(self, svg: bytes, dpi: int, to: Path) -> None:
        self.cairosvg.svg2png(
            svg,
            scale = dpi / self.DEFAULT_DPI,
            write_to = str(to),
            background_color = self.WHITE
        )


class WandRenderer(Renderer):
    """Second-choice renderer: slower, but still a clean interface.

    Requires the Python package ``Wand`` to be installed, which in turn depends
    on ImageMagick.

    Installing ``ImageMagick``

    Installing ``Wand``
    """

    Image: Any
    background: Any

    def __init__(self):
        try:
            from wand.color import Color
            from wand.image import Image

            self.Image = Image
            self.background = Color('white')
            self._confirm(True)
        except Exception as e:
            self._confirm(False, e)
    def _save(self, svg: bytes, dpi: int, to: Path) -> None:
        with open(to, "wb") as f:
            with self.Image() as image:
                image.read(
                    blob=svg,
                    background=self.background,
                    resolution=dpi,
                )
                f.write(image.make_blob("png32"))


class WindowsInkscapeRenderer(Renderer):
    """Fallback renderer for Windows: it works, but is hacky and bad.

    Requires Inkscape to be installed.
    """

    INKSCAPE_DIR_CANDIDATES: List[Path] = [
        Path("C:\\Program Files (x86)\\Inkscape"),
        Path("C:\\Program Files\\Inkscape"),
    ]
    inkscape_dir: Path


    def __init__(self):
        if os.name != 'nt':
            self._works = False
            return
        for candidate in self.INKSCAPE_DIR_CANDIDATES:
            if candidate.is_dir():
                try:
                    check_call([
                        "cd", str(candidate), "&&", "inkscape", "--version"
                    ])
                    self.inkscape_dir = candidate
                    self._confirm(True)
                except CalledProcessError as e:
                    self._confirm(False, e)

    def _save(self, svg: bytes, dpi: int, to: Path) -> None:
        with NamedTemporaryFile("w") as temp:
            temp.write(str(svg))
            check_call([
                "cd", str(self.inkscape_dir), "&&", "inkscape",
                "--export-type=png",
                f"--export-filename={to}",
                f"--export-dpi={dpi}",
                temp.name
            ])


_renderer: Renderer
__choices__: List[Type[Renderer]] = [
    CairoRenderer,
    WandRenderer,
    WindowsInkscapeRenderer,
]

for _renderer_type in __choices__:
    _candidate = _renderer_type()
    if _candidate.works:
        _renderer = _candidate
        break

if '_renderer' not in locals():
    raise RendererError(f"None of the defined renderers seem to work...")


def save_svg(svg: bytes, dpi: int, to: Path) -> None:
    """Save SVG to a PNG image using the renderer selected for this system.

    Parameters
    ----------
    svg: bytes
        An SVG image as XML bytes
    dpi: int
        The DPI (dots per inch) to render the SVG at
    to: Path
        Where to save the PNG image

    Raises
    ------
    RendererError
        if none of the available renderers work on this system
    """
    _renderer.save(svg, dpi, to)

