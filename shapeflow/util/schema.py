"""Utility funcitons for JSON schemas
"""

from pathlib import Path
from typing import List, Optional, Any, Union
from argparse import ArgumentParser
from pydantic import DirectoryPath, FilePath


TITLE = "title"
DESCRIPTION = "description"
TYPE = "type"
PROPERTIES = "properties"
DEFAULT = "default"

OBJECT = "object"
STRING = "string"
INTEGER = "integer"


def _pytype2schematype(type_) -> Optional[str]:
    """Converts a Python type to the corresponding JSON schema type

    Parameters
    ----------
    type_

    Returns
    -------
    str
    """
    if type_ is None:
        return None
    elif type_ is int:
        return "integer"
    elif type_ is float:
        return "number"
    elif type_ is str:
        return "string"
    elif type_ is Path:
        return "path"
    else:
        raise ValueError(f"Unexpected argument type '{type_}'")


def _normalize_default(default: Any) -> Union[None, str, int, float, bool]:
    if type(default) in (type(None), str, int, float, bool):
        return default
    elif issubclass(type(default), Path):
        return str(default)
    else:
        raise ValueError(f"Unexpected default type '{type(default)}'")


def argparse2schema(parser: ArgumentParser) -> dict:
    """Returns the JSON schema of an ``argparse.ArgumentParser``.

    Doesn't handle accumulating arguments.

    Parameters
    ----------
    parser: ArgumentParser
        an ``ArgumentParser`` instance

    Returns
    -------
    dict
        The JSON schema of this ``ArgumentParser``
    """
    return {
        TITLE: parser.prog,
        DESCRIPTION: parser.description,
        TYPE: OBJECT,
        PROPERTIES: {
            action.dest: {
                TITLE: action.dest,
                DESCRIPTION: action.help,
                TYPE: _pytype2schematype(action.type)
                    if action.type is not None else "boolean",
                DEFAULT: _normalize_default(action.default)
            }
            for action in parser._actions if action.dest != "help"
        }
    }


def args2call(parser: ArgumentParser, args: dict) -> List[str]:
    """Formats a dict into a list of call arguments for a specific parser.

    Parameters
    ----------
    parser: ArgumentParser
        The ``ArgumentParser`` instance to format the arguments for
    request: dict
        A ``dict`` of arguments

    Raises
    ------
    ValueError
        If the arguments in ``args`` don't match those of ``parser``

    Returns
    -------
    List[str]
        The arguments in ``args`` as a list of strings
    """
    call_positionals: List[str] = []
    call_optionals: List[str] = []

    actions = {a.dest: a for a in parser._actions}
    positionals = [a.dest for a in parser._positionals._group_actions]
    optionals = {a.dest: a for a in parser._optionals._group_actions}

    for key in [a.dest for a in parser._actions if a.required]:
        if key not in args:
            raise ValueError(f"Parser '{parser.prog}': "
                             f"missing required argument '{key}'")

    for key, value in args.items():
        if key not in actions.keys():
            raise ValueError(f"Parser '{parser.prog}': "
                             f"argument '{key}' is not allowed")
        if actions[key].type is not None:
            if type(value) is not actions[key].type:
                raise ValueError(f"Parser '{parser.prog}': "
                                 f"Argument '{key}' should be "
                                 f"{actions[key].type}, "
                                 f"but was given {type(value)} instead")
        else:
            if type(value) is not bool:
                raise ValueError(f"Parser '{parser.prog}': "
                                 f"Flag {key} value type should be bool, "
                                 f"but was given {type(value)} instead")

        if key in positionals:
            call_positionals.insert(positionals.index(key), str(value))
        elif key in optionals.keys():
            if optionals[key].type is not None:
                call_optionals.append(f"--{key}")
                call_optionals.append(str(value))
            else:
                if value:
                    call_optionals.append(f"--{key}")

    return call_positionals + call_optionals

