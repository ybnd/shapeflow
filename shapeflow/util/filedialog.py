from typing import List, Optional

import os
import subprocess


__VIDEO_PATTERN__ = "*.mp4 *.avi *.mov *.mpv *.mkv"
__DESIGN_PATTERN__ = "*.svg"


def has_zenity():
    try:
        with open(os.devnull, 'w') as null:
            return not subprocess.check_call(
                ['zenity', '--version'], stdout=null
            )
    except FileNotFoundError:
        return False


def load_file_dialog(title: str = None, pattern: str = None, pattern_description: str = '') -> Optional[str]:
    if title is None:
        title = 'Load...'

    if pattern is None:
        pattern = ""

    if has_zenity():
        try:
            if len(pattern) > 0:
                p = subprocess.Popen(
                    [
                        'zenity', '--file-selection',
                        '--file-filter', pattern,
                    ], stdout=subprocess.PIPE, stderr=subprocess.PIPE
                )
            else:
                p = subprocess.Popen(
                    [
                        'zenity', '--file-selection',
                    ], stdout=subprocess.PIPE, stderr=subprocess.PIPE
                )
            out, err = p.communicate()
            if out:
                return out.rstrip().decode('utf-8')
            else:
                return None
        except subprocess.CalledProcessError:
            return None

    else:
        try:
            if len(pattern) > 0:
                p = subprocess.Popen(
                    [
                        'python', 'shapeflow/util/tk_filedialog.py',
                        '--load', '--title', title, 
                        '--filetypes', pattern,
                        '--filedesc', pattern_description,
                    ], stdout=subprocess.PIPE, stderr=subprocess.PIPE
                )
            else:
                p = subprocess.Popen(
                    [
                        'python', 'shapeflow/util/tk_filedialog.py',
                        '--load', '--title', title, 
                    ], stdout=subprocess.PIPE, stderr=subprocess.PIPE
                )
            out, err = p.communicate()
            if out:
                return out.rstrip().decode('utf-8')
            else:
                return None
        except subprocess.CalledProcessError:
            return None


def save_file_dialog(title: str = None, pattern: str = None, pattern_description: str = '') -> Optional[str]:
    if title is None:
        title = 'Save as...'

    if pattern is None:
        pattern = ""

    if has_zenity():
        try:
            if len(pattern) > 0:
                p = subprocess.Popen(
                    [
                        'zenity', '--file-selection', '--save'
                        '--file-filter', pattern,
                    ], stdout=subprocess.PIPE, stderr=subprocess.PIPE
                )
            else:
                p = subprocess.Popen(
                    [
                        'zenity', '--file-selection', '--save'
                    ], stdout=subprocess.PIPE, stderr=subprocess.PIPE
                )
            out, err = p.communicate()
            if out:
                return out.strip().decode('utf-8')
            else:
                return None
        except subprocess.CalledProcessError:
            return None

    else:
        try:
            # todo: doesn't work when debugging on Windows!
            if len(pattern) > 0:
                p = subprocess.Popen(
                    [
                        'python', 'shapeflow/util/tk_filedialog.py',
                        '--save', '--title', title, 
                        '--filetypes', pattern,
                        '--filedesc', pattern_description,
                    ], stdout=subprocess.PIPE, stderr=subprocess.PIPE
                )
            else:
                p = subprocess.Popen(
                    [
                        'python', 'shapeflow/util/tk_filedialog.py',
                        '--save', '--title', title, 
                    ], stdout=subprocess.PIPE, stderr=subprocess.PIPE
                )
            out, err = p.communicate()
            if out:
                return out.rstrip().decode('utf-8')
            else:
                return None
        except subprocess.CalledProcessError:
            return None
