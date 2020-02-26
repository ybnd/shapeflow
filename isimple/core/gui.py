import os
import sys
import subprocess

import tkinter.ttk as ttk
import tkinter.filedialog as tkfd

import abc
from typing import List

from isimple.core.common import Endpoint


def has_zenity():
    with open(os.devnull, 'w') as null:
        return not subprocess.check_call(['zenity', '--version'], stdout=null)


def load_file_dialog(title: str = None, patterns: List[str] = None, patterns_str: str = None):
    if title is None:
        title = 'Load...'

    if patterns is None:
        patterns = []

    if has_zenity():
        try:
            if len(patterns) > 0:
                p = subprocess.Popen(
                    [
                        'zenity', '--file-selection',
                        f'--file-filter', ' '.join(patterns),
                    ], stdout=subprocess.PIPE, stderr=subprocess.PIPE
                )
            else:
                p = subprocess.Popen(
                    [
                        'zenity', '--file-selection',
                    ], stdout=subprocess.PIPE, stderr=subprocess.PIPE
                )
            out, err = p.communicate()
            if not err:
                return out.rstrip().decode('utf-8')
        except subprocess.CalledProcessError:
            return None

    else:
        if len(patterns) > 0:
            return tkfd.askopenfilename(
                title=title,
                filetypes=[(patterns_str, ' '.join(patterns))]
            )
        else:
            return tkfd.askopenfilename(
                title=title,
            )


def save_file_dialog(title: str = None, patterns: List[str] = None, patterns_str: str = None):
    if title is None:
        title = 'Save as...'

    if patterns is None:
        patterns = []

    if has_zenity():
        try:
            if len(patterns) > 0:
                p = subprocess.Popen(
                    [
                        'zenity', '--file-selection', '--save'
                        f'--file-filter', ' '.join(patterns),
                    ], stdout=subprocess.PIPE, stderr=subprocess.PIPE
                )
            else:
                p = subprocess.Popen(
                    [
                        'zenity', '--file-selection', '--save'
                    ], stdout=subprocess.PIPE, stderr=subprocess.PIPE
                )
            out, err = p.communicate()
            if not err:
                return out.strip().decode('utf-8')
        except subprocess.CalledProcessError:
            return None

    else:
        if len(patterns) > 0:
            return tkfd.asksaveasfilename(
                title=title,
                filetypes=[(patterns_str, ' '.join(patterns))]
            )
        else:
            return tkfd.asksaveasfilename(
                title=title,
            )


class guiElement(abc.ABC):
    """Abstract class for GUI elements
    """
    def __init__(self):
        pass

    def build(self):
        pass


class guiPane(guiElement):
    """Abstract class for a GUI pane
    """
    def __init__(self):
        super().__init__()

    def build(self):
        pass


class guiWindow(guiElement):
    """Abstract class for a GUI window
    """
    _endpoints: List[Endpoint]

    def __init__(self):
        super().__init__()

    def open(self):  # todo: should check if all callbacks have been provided
        pass

    def close(self):
        pass