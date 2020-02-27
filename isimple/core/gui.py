import os
import sys
import subprocess

from typing import Union, Dict, Callable

import tkinter
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


class EntryPopup(ttk.Entry):
    """Pop-up widget to allow value editing in TreeDict
    """
    def __init__(self, parent, iid, index, item, callback, **kw):
        ''' If relwidth is set, then width is ignored '''
        super().__init__(parent, **kw)
        self.tv = parent
        self.iid = iid
        self.item = item
        self.callback = callback

        self.index = index
        self.insert(0, self.tv.item(self.iid, "values")[index])
        # self['state'] = 'readonly'
        # self['readonlybackground'] = 'white'
        # self['selectbackground'] = '#1BA1E2'
        self['exportselection'] = False

        self.focus_force()
        self.bind("<Return>", self.on_return)  # todo: this doesn't work too well. Also bind numpad enter & "click away / unfocus"
        self.bind("<KP_Enter>", self.on_return)
        self.bind("<Control-a>", self.select_all)
        self.bind("<Escape>", lambda *ignore: self.destroy())
        self.bind("<FocusOut>", lambda *ignore: self.destroy())

    def on_return(self, event):
        v = list(self.tv.item(self.iid, "values"))
        v[self.index] = self.get()
        self.tv.item(self.iid, values=tuple(v))  # todo: also update self.tv._data !!!

        self.item = type(self.item)(v[0])

        self.callback()
        self.destroy()

    def select_all(self, *ignore):
        ''' Set selection on the whole text '''
        self.selection_range(0, 'end')

        # returns 'break' to interrupt default key-bindings
        return 'break'


class TreeDict(object):
    """An editable representation of a dictionary in a ttk.Treeview
    """

    # cheated off of
    #   - https://github.com/r2123b/tkinter-ttk-Treeview-Simple-Demo/blob/master/SimpleTreeview.py
    #   - https://stackoverflow.com/questions/51762835/
    #   - https://stackoverflow.com/questions/18562123/

    _tk: Union[tkinter.Tk, tkinter.Misc]
    _tree: ttk.Treeview
    _data: dict

    _values: Dict[str, list]
    _edit_callback: Callable[[dict], dict]

    _data_iid: dict

    def __init__(self, tk: Union[tkinter.Tk, tkinter.Misc], data: dict, callback: Callable[[dict], dict]):
        self._tk = tk
        self._edit_callback = callback  # type: ignore
        self.update(data)

        self._tree.bind("<Double-1>", self.edit)

    def set(self, data: dict):
        self._data = data
        self.build()

    def set_value(self, iid, value):
        raise NotImplementedError

    def callback(self):
        self._data = self._edit_callback(self._data)  # callback to handler; validate & update self._data

    def build(self):
        self._tree = ttk.Treeview(
            self._tk, show="tree"
        )
        self._iid_mapping = {}

        def handle_item(self, key, item, parent: str = ''):
            if (isinstance(item, list) or isinstance(item, tuple)) and \
                    not any(isinstance(i, dict) for i in item):
                p = self._tree.insert(parent, 'end', text=key, values=[str(item)])
                self._iid_mapping[p] = item
            elif (isinstance(item, list) or isinstance(item, tuple)) and \
                    any(isinstance(i, dict) for i in item):
                p = self._tree.insert(parent, 'end', text=key)
                self._iid_mapping[p] = item
                for i, subitem in enumerate(item):
                    if 'name' in subitem:
                        title = subitem['name']
                    else:
                        title = f"{key} {i}"
                    handle_item(self, title, subitem, p)
            elif isinstance(item, dict):
                p = self._tree.insert(parent, 'end', text=key)
                self._iid_mapping[p] = item
                for sk, sv in item.items():
                    handle_item(self, sk, sv, p)
            else:
                p = self._tree.insert(parent, 'end', text=key, values=[item])
                self._iid_mapping[p] = item
            self._tree.item(p, open=True)  # expands everything by default

        for k, v in self._data.items():
            handle_item(self, k, v)

        self._tree["columns"] = ('', '')  # doesn't work with *one* column or when not set, for some reason


    def edit(self, event):
        ''' Executed, when a row is double-clicked. Opens
        read-only EntryPopup above the item's column, so it is possible
        to select text '''

        # close previous popups
        if hasattr(self, 'entryPopup'):
            try:
                self.entryPopup.on_return(None)
            except Exception:
                pass
            self.entryPopup.destroy()
            del self.entryPopup

        # what row and column was clicked on
        rowid = self._tree.identify_row(event.y)
        column = self._tree.identify_column(event.x)

        print(f"Selected row {rowid} & column {column}")

        # Don't allow editing keys
        if column != '#0':
            # get column position info
            x, y, width, height = self._tree.bbox(rowid, column)

            print(f"Cell: x{x}, y{y}, x{width}, h{height}")

            # y-axis offset
            pady = height // 2
            # pady = 0

            # place Entry popup properly
            index = int(column[1:]) - 1
            self.entryPopup = EntryPopup(self._tree, rowid, index, self._iid_mapping[rowid], self.callback)
            self.entryPopup.place(x=x, y=y + pady, anchor='w', width=100)  # todo: set x to start at the right column, relwidth to cover the whole column

    def update(self, data: dict):
        self.set(data)
        self._tree.pack()
        self._tk.update()



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