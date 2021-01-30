import copy
import datetime
import glob
import os
import shutil
from contextlib import contextmanager
from enum import Enum
from multiprocessing import cpu_count
from pathlib import Path
from typing import Dict, Any, Type, TypeVar, Generic, Tuple

import json
from pydantic import BaseModel, Field, DirectoryPath, validator, FilePath

from shapeflow import ROOTDIR
from shapeflow.core import RootException
from shapeflow.util import Singleton


class SettingsError(RootException):
    pass


class Category(BaseModel):
    """Abstract application settings
    """

    class Config:
        validate_assignment = True

    def to_dict(self) -> dict:
        """
        Returns
        -------
        dict
            Application settings as a dict

        """
        d: dict = {}
        for k,v in self.__dict__.items():
            if isinstance(v, Category):
                d.update({
                    k:v.to_dict()
                })
            elif isinstance(v, Enum):
                d.update({
                    k:v.value
                })
            elif isinstance(v, Path):
                d.update({
                    k:str(v)  # type: ignore
                })            # todo: fix ` Dict entry 0 has incompatible type "str": "str"; expected "str": "Dict[str, Any]" `
            else:
                d.update({
                    k:v
                })
        return d

    @contextmanager
    def override(self, overrides: dict):  # todo: consider deprecating in favor of mocks
        """Override some parameters of the settings in a context.
        Settings will only be modified within this context and restored to
        their previous values afterwards.
        Usage::
            with settings.override({"parameter": "override value"}):
                <do something>

        Parameters
        ----------
        overrides: dict
            A ``dict`` mapping field names to values with which to
            override those fields
        """
        originals: dict = {}
        try:
            for attribute, value in overrides.items():
                originals[attribute] = copy.deepcopy(
                    getattr(self, attribute)
                )
                setattr(self, attribute, value)
            yield
        finally:
            for attribute, original in originals.items():
                setattr(self, attribute, original)

    @classmethod
    def _validate_filepath(cls, value):
        if not isinstance(value, Path):
            value = Path(value)

        if not value.exists() and not value.is_file():
            value.touch()

        return value

    @classmethod
    def _validate_directorypath(cls, value):
        if not isinstance(value, Path):
            value = Path(value)

        if not value.exists() and not value.is_dir():
            value.mkdir()

        return value

    @classmethod
    def schema(cls, by_alias: bool = True, ref_template: str = '') -> Dict[str, Any]:
        """Inject title & description into ``pydantic`` schema.

        These get lost due to some `bug`_ with ``Enum``.

        .. _bug: https://github.com/samuelcolvin/pydantic/pull/1749
        """

        schema = super().schema(by_alias)

        def _inject(class_: Type[Category], schema, definitions):
            for field in class_.__fields__.values():
                if 'properties' in schema and field.alias in schema['properties']:
                    if 'title' not in schema['properties'][field.alias]:
                        schema['properties'][field.alias][
                            'title'] = field.field_info.title
                    if field.field_info.description is not None and 'description' not in schema['properties'][field.alias]:
                        schema['properties'][field.alias]['description'] = field.field_info.description
                if issubclass(field.type_, Category):
                    # recurse into nested _Settings classes
                    _inject(field.type_, definitions[field.type_.__name__], definitions)
            return schema

        return _inject(cls, schema, schema['definitions'])


_SETTINGS_FILE = ROOTDIR / 'settings.json'


class Settings(metaclass=Singleton):
    _categories: Dict[Type[Category], Category] = {}
    _loaded: Dict[str, dict] = {}

    def __init__(self):
        self._load()
        self.save()

    def add(self, category: Type[Category]) -> None:
        """Add a category to the Settings

        Parameters
        ----------
        category : Type[Category]
            The category class to add

        Returns
        -------

        """
        self._categories[category] = self._initialize_from_loaded(category)

    def get(self, type: Type[Category]) -> Category:
        if type is None:
            raise SettingsError('no category class provided')
        if type not in self._categories:
            self.add(type)
        return self._categories[type]

    def _load(self):
        """Load from JSON
        """

        if _SETTINGS_FILE.is_file():
            with open(_SETTINGS_FILE, 'r') as f:
                self._loaded = json.load(f)

            for category in self._categories.keys():
                self._initialize_from_loaded(category)

                # # Move the previous log file to ROOTDIR/log  # todo: move to shapeflow.core.logging
                # if Path(settings.log.path).is_file():
                #     shutil.move(
                #         str(settings.log.path),  # todo: convert to pathlib
                #         os.path.join(
                #             settings.log.dir,
                #             datetime.datetime.fromtimestamp(
                #                 os.path.getmtime(settings.log.path)
                #             ).strftime(
                #                 settings.format.datetime_format_fs) + '.log'
                #         )
                #     )
                #
                # # If more files than specified in ini.log.keep, remove the oldest
                # files = glob.glob(os.path.join(settings.log.dir,
                #                                '*.log'))  # todo: convert to pathlib
                # files.sort(key=lambda f: os.path.getmtime(f), reverse=True)
                # while len(files) > settings.log.keep:
                #     os.remove(files.pop())

    def _initialize_from_loaded(self, category: Type[Category]) -> Category:
        if category.__name__ in self._loaded:
            return category(**self._loaded[category.__name__])
        else:
            return category()

    def save(self):
        with open(_SETTINGS_FILE, 'w+') as f:
            json.dump(self.as_dict(), f, indent=2)

    def as_dict(self) -> dict:
        return {type.__name__: category.dict()
                for (type, category) in self._categories.items()}

    def update(self, d: dict) -> dict:
        types = self._categories.keys()
        for type in types:
            if type.__name__ in d:
                self._loaded[type.__name__] = d[type.__name__]
                self._categories[type] = self._initialize_from_loaded(type)
        return self.as_dict()


settings = Settings()


class FormatSettings(Category):
    """Formatting settings
    """
    datetime_format: str = Field(default='%Y/%m/%d %H:%M:%S.%f', title="date/time format")
    """Base ``datetime`` `format string <dtfs_>`_. 
    Defaults to ``'%Y/%m/%d %H:%M:%S.%f'``.

    .. _dtfs: https://docs.python.org/3/library/datetime.html#strftime-strptime-behavior
    """
    datetime_format_fs: str = Field(default='%Y-%m-%d_%H-%M-%S', title="file system date/time format")
    """Filesystem-safe ``datetime`` `format string <dtfs_>`_. 
    Used to append date & time to file names.
    Defaults to ``'%Y-%m-%d_%H-%M-%S'``.

    .. _dtfs: https://docs.python.org/3/library/datetime.html#strftime-strptime-behavior
    """


class ResultSaveMode(str, Enum):
    """Where (or whether) to save the results of an analysis
    """
    skip = "skip"
    """Don't save results at all
    """
    next_to_video = "next to video file"
    """Save results in the same directory as the video file that was analyzed
    """
    next_to_design = "next to design file"
    """Save results in the same directory as the design file that was analyzed
    """
    directory = "in result directory"
    """Save results in their own directory at 
    :attr:`shapeflow.ApplicationSettings.result_dir`
    """


class ApplicationSettings(Category):
    """Application settings.
    """
    save_state: bool = Field(default=True, title="save application state on exit")
    """Whether to save the application state when exiting the application
    """
    load_state: bool = Field(default=True, title="load application state on start")
    """Whether to load the application state when starting the application
    """
    state_path: FilePath = Field(default=str(ROOTDIR / 'state'), title="application state file")
    """Where to save the application state
    """
    recent_files: int = Field(default=16, title="# of recent files to fetch")
    """The number of recent files to show in the user interface
    """
    video_pattern: str = Field(default="*.mp4 *.avi *.mov *.mpv *.mkv", title="video file pattern")
    """Recognized video file extensions. 
    Defaults to ``"*.mp4 *.avi *.mov *.mpv *.mkv"``.
    """
    design_pattern: str = Field(default="*.svg", title="design file pattern")
    """Recognized design file extensions. 
    Defaults to ``"*.svg"``.
    """
    save_result_auto: ResultSaveMode = Field(default=ResultSaveMode.next_to_video, title="result save mode (auto)")
    """Where or whether to save results after each run of an analysis
    """
    save_result_manual: ResultSaveMode = Field(default=ResultSaveMode.next_to_video, title="result save mode (manual)")
    """Where or whether to save results that are exported manually 
    via the user interface
    """
    result_dir: DirectoryPath = Field(default=str(ROOTDIR / 'results'), title="result directory")
    """The path to the result directory
    """
    cancel_on_q_stop: bool = Field(default=False, title="cancel running analyzers when stopping queue")
    """Whether to cancel the currently running analysis when stopping a queue.
    
    Defaults to ``False``, i.e. the currently running analysis will be 
    completed first.
    """
    threads: int = Field(default=cpu_count(), title="# of threads")
    f"""The number of threads the server uses. Defaults to {cpu_count()}, the 
    number of logical cores of your machine's CPU.
    """

    _validate_dir = validator('result_dir', allow_reuse=True, pre=True)(
        Category._validate_directorypath)
    _validate_state_path = validator('state_path', allow_reuse=True, pre=True)(
        Category._validate_filepath)

    @validator('threads', pre=True, allow_reuse=True)
    def _validate_threads(cls, value):
        if value < 8:
            return 8  # At least 8 threads to run decently
        else:
            return value