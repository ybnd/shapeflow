"""Design file handling

Adapted from https://github.com/ybnd/OnionSVG
"""

from pathlib import Path
from typing import Union

from lxml.etree import fromstring

from shapeflow.core import get_logger
from shapeflow.design.onions import DesignFileError, Peeler


log = get_logger(__name__)


def check_design(file: Union[Path, str]) -> None:
    """Check whether the file is a valid design file.

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
        raise DesignFileError(f"Invalid SVG file: {file} ({e})")


def peel(file: Union[Path, str], dpi: int, dir: Union[Path, str]) -> None:
    """Render a design layer per layer

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
