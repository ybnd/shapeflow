from typing import List, Optional

import os
import subprocess


__VIDEO_PATTERNS__ = ["*.mp4", "*.avi", "*.mov", "*.mpv", "*.mkv"]
__DESIGN_PATTERNS__ = ["*.svg"]


def has_zenity():
    try:
        with open(os.devnull, 'w') as null:
            return not subprocess.check_call(
                ['zenity', '--version'], stdout=null
            )
    except FileNotFoundError:
        return False


def load_file_dialog(title: str = None, patterns: List[str] = None, patterns_str: str = '') -> Optional[str]:
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
                        '--file-filter', ' '.join(patterns),
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
            if len(patterns) > 0:
                p = subprocess.Popen(
                    [
                        'python', 'shapeflow/util/tk_filedialog.py',
                        '--load', '--title', title, 
                        '--filetypes', ' '.join(patterns),
                        '--filedesc', patterns_str,
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


def save_file_dialog(title: str = None, patterns: List[str] = None, patterns_str: str = '') -> Optional[str]:
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
                        '--file-filter', ' '.join(patterns),
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
            if len(patterns) > 0:
                p = subprocess.Popen(
                    [
                        'python', 'shapeflow/util/tk_filedialog.py',
                        '--save', '--title', title, 
                        '--filetypes', ' '.join(patterns),
                        '--filedesc', patterns_str,
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


def select_video() -> Optional[str]:
    return load_file_dialog(
        "Select video file...",
        patterns=__VIDEO_PATTERNS__
    )


def select_design() -> Optional[str]:
    return load_file_dialog(
        "Select design file...",
        patterns=__DESIGN_PATTERNS__
    )
