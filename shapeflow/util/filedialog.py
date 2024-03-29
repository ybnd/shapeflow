import os
import abc
from typing import List, Optional, Any
import subprocess as sp


class _FileDialog(metaclass=abc.ABCMeta):
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

    def _resolve(self, method: str, kwargs: dict) -> dict:
        """ Resolve empty arguments to defaults """
        return {
            **self._defaults['all'],
            **(self._defaults[method] if method in self._defaults else {}),
            **kwargs
        }

    @abc.abstractmethod
    def _load(self, **kwargs) -> Optional[str]:
        """ Loading functionality to be implemented by child classes """

    @abc.abstractmethod
    def _save(self, **kwargs) -> Optional[str]:
        """ Saving functionality to be implemented by child classes """


class _SubprocessTkinter(_FileDialog):
    ok = True

    def _load(self, **kwargs) -> Optional[str]:
        return self._call('--load', self._to_args(kwargs))

    def _save(self, **kwargs) -> Optional[str]:
        return self._call('--save', self._to_args(kwargs))

    def _call(self, command: str, args: list) -> Optional[str]:
        p = sp.Popen(
            [
                'python', 'shapeflow/util/tk-filedialog.py', command, *args
            ], stdout=sp.PIPE, stderr=sp.PIPE
        )
        out, _ = p.communicate()
        if out != b'':
            return out.strip().decode('utf-8')
        else:
            raise ValueError(f"No file selected")

    def _to_args(self, kwargs: dict) -> list:
        args = []
        for kw, arg in kwargs.items():
            args.append("--" + kw)
            args.append(arg)
        return args



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
        except sp.CalledProcessError:
            pass
        raise ValueError(f"No file selected")


class _Windows(_FileDialog):
    GetOpenFileNameW: Any
    GetSaveFileNameW: Any

    def __init__(self):
        from win32gui import GetOpenFileNameW, GetSaveFileNameW
        self.GetOpenfileNameW = GetOpenFileNameW
        self.GetSaveFileNameW = GetSaveFileNameW

    def _resolve(self, method: str, kwargs: dict) -> dict:
        kwargs = super()._resolve(method, kwargs)
        kwargs["Title"] = kwargs.pop("title")
        kwargs["Filter"] = f"{kwargs.pop('pattern_description')}\0" \
                           f"{kwargs.pop('pattern').replace(' ', ';')}\0"

        return kwargs

    def _load(self, **kwargs) -> Optional[str]:
        file, _, _ = self.GetOpenFileNameW(**kwargs)
        return file

    def _save(self, **kwargs) -> Optional[str]:
        file, _, _ = self.GetSaveFileNameW(**kwargs)
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
        filedialog = _SubprocessTkinter()
else:
    filedialog = _Windows()
