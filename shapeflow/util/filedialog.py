import os
import abc
from typing import List, Optional
import subprocess as sp
import tkinter
import tkinter.filedialog
from win32gui import GetOpenFileNameW, GetSaveFileNameW


class _FileDialog(abc.ABC):
    ok: bool = False

    _defaults: dict = {
        'load': {
            'title': 'Load a file...',
        },
        'save': {
            'title': 'Save a file...',
        },
        'all': {
            'pattern': None,
            'pattern_description': None,
        }
    }

    def load(self, **kwargs) -> Optional[str]:
        """ Show a load dialog """
        return self._load(**self._resolve('load', kwargs))

    def save(self, **kwargs) -> Optional[str]:
        """ Show a save dialog """
        return self._save(**self._resolve('save', kwargs))

    @classmethod
    def _resolve(self, method: str, kwargs: dict) -> dict:
        """ Resolve empty arguments to defaults """
        return {
            **self._defaults['all'],
            **(self._defaults[method] if method in self._defaults else {}),
            **kwargs
        }

    @abc.abstractmethod
    def _load(self, **kwargs) -> Optional[str]:
        raise NotImplementedError

    @abc.abstractmethod
    def _save(self, **kwargs) -> Optional[str]:
        raise NotImplementedError


class _Tkinter(_FileDialog):
    ok = True

    _map = {
        'title': 'title',
        'pattern': 'filetypes',
        'pattern_description': 'filedesc',
    }

    def __init__(self):
        try:
            root = tkinter.Tk()
            root.withdraw()
        except Exception as e:
            print("Can't initialize tkinter!") # todo: clean this up

    def _load(self, **kwargs) -> Optional[str]:
        return tkinter.filedialog.askopenfilename(**self._translate(kwargs))

    def _save(self, **kwargs) -> Optional[str]:
        return tkinter.filedialog.asksaveasfilename(**self._translate(kwargs))

    def _translate(self, kwargs: dict) -> dict:
        return { self._map[k]:v for k,v in kwargs.items() }


def _has_zenity():
    try:
        return not sp.call(['zenity', '--version'], stdout=sp.DEVNULL)
    except FileNotFoundError:
        return False


class _Zenity(_FileDialog):
    _map = {
        'title': '--title',
        'pattern': '--file-filter',
    }
    def __init__(self):
        self.ok = _has_zenity()

    def _load(self, **kwargs) -> Optional[str]:
        return self._call(self._compose(False, kwargs))

    def _save(self, **kwargs) -> Optional[str]:
        return self._call(self._compose(True, kwargs))

    def _compose(self, save: bool, kwargs: dict) -> List[str]:
        command = ['zenity', '--file-selection']

        if save:
            command += ['--save']

        for k, v in kwargs.items():
            if v is not None and k in self._map:
                command += [self._map[k], v]

        return command

    def _call(self, command: List[str]) -> Optional[str]:
        try:
            p = sp.Popen(command, stdout=sp.PIPE)
            out, err = p.communicate()
            if out:
                return out.rstrip().decode('utf-8')
            else:
                return None
        except sp.CalledProcessError:
            return None


class _Windows(_FileDialog):
    def __init__(self):
        self.ok = os.name == 'nt'

    def _resolve(self, method: str, kwargs: dict) -> dict:
        kwargs = super()._resolve(method, kwargs)
        kwargs["Title"] = kwargs.pop("title")
        kwargs["Filter"] = f"{kwargs.pop('pattern_description')}\0" \
                           f"{kwargs.pop('pattern').replace(' ', ';')}\0"

        return kwargs

    def _load(self, **kwargs) -> Optional[str]:
        file, _, _ = GetOpenFileNameW(**kwargs)
        return file

    def _save(self, **kwargs) -> Optional[str]:
        file, _, _ = GetSaveFileNameW(**kwargs)
        return file


filedialog: _FileDialog

if os.name != "nt":
    # try using zenity by default
    filedialog = _Zenity()
    """Cross-platform file dialog.
    
    Tries to use `zenity <https://help.gnome.org/users/zenity/stable/>`_
    if available, because ``tkinter`` looks fugly in GNOME don't @ me.
    
    Defaults to ``tkinter`` to support basically any platform.
    """
    # if zenity doesn't work (e.g. it's not installed),
    # default to tkinter.
    if not filedialog.ok:
        filedialog = _Tkinter()
else:
    filedialog = _Windows()
