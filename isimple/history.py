import os
import abc
import time
import datetime
import json

from typing import Optional, Tuple, Union
import multiprocessing

import numpy as np

from isimple.core.common import RootException
from isimple.util import hash_file, ndarray2str, str2ndarray
from isimple.core import settings
from isimple.core import get_logger
from isimple.video import VideoAnalyzer

from isimple.dbcore import Model, Database, types, MatchQuery


log = get_logger(__name__)


class NoGetterModel(Model):
    @classmethod
    def _getters(cls):
        return {}


class ResultsModel(NoGetterModel):
    _table = 'results'
    _flex_table = 'result_attributes'
    _fields: dict = {
        'id': types.PRIMARY_ID,
        'analysis': types.FOREIGN_ID,

        'feature': types.STRING,
        'data': types.STRING,
        'added': types.DATE,
    }
    _search_fields = (
        'analysis', 'feature',
    )


class FileModel(NoGetterModel):
    _path: str
    _hash_q: Optional[multiprocessing.Queue]
    _parent: Optional[Tuple[Model, str]]

    def __init__(self, *args, **kwargs):
        super().__init__()
        self._hash_q = None
        self._parent = None

    def queue_hash(self, path: str):
        self._path = path
        if self._check_file():
            self._hash_q = hash_file(self._path)
        else:
            raise ValueError

    def _check_file(self):
        return self._check_file_exists()

    def _check_file_exists(self) -> bool:
        if self._path is not None:
            return os.path.isfile(self._path)
        else:
            return False

    def hash(self) -> str:
        try:
            assert self._hash_q is not None
            return self._hash_q.get()
        except AttributeError:
            raise RootException(f"{self.__class__.__qualname__}: hash() "
                                "was called before queue_hash()")

    def set_parent(self, model: Model, attribute: str):
        self._parent = (model, attribute)

    def resolve(self):
        """Check this file's hash against the database; if the file is already
            listed, remove it from the database and set the parent's file to
            the matching file instead.
        """
        if hasattr(self, '_hash_q') and self._hash_q is not None:
            if self._hash_q.qsize():
                hash = self.hash()
                match = self._db._fetch(self.__class__, MatchQuery('hash', hash))  # todo: is there a cleaner way to do this?

                if any(hash == m['hash'] for m in match):
                    match = match.get()
                    match._db = self._db  # todo: is there a cleaner way to do this?
                    self.remove()
                    setattr(*self._parent, match)
                else:
                    self.update({
                        'path': self._path,
                        'hash': hash,
                    })
            else:
                pass
        else:
            pass


class RoiModel(NoGetterModel):
    _table = 'rois'
    _flex_table = 'roi_attributes'
    _fields: dict = {
        'id': types.PRIMARY_ID,

        'video': types.FOREIGN_ID,
        'design': types.FOREIGN_ID,
        'analysis': types.FOREIGN_ID,

        'roi': types.STRING,

        'added': types.DATE,
    }


class VideoFileModel(FileModel):
    _table = 'video_files'
    _flex_table = 'video_file_attributes'
    _fields: dict = {
        'id': types.PRIMARY_ID,
        'hash': types.STRING,
        'path': types.STRING,
        'added': types.DATE,
    }
    _search_fields = ('path', 'hash')
    LIST_SEPARATOR = '\n'

    def _check_file(self):
        return super()._check_file() # todo: override with video-specific stuff


class DesignFileModel(FileModel):
    _table = 'design_files'
    _flex_table = 'design_file_attributes'
    _fields: dict = {
        'id': types.PRIMARY_ID,
        'hash': types.STRING,
        'path': types.STRING,
        'added': types.DATE,
    }
    _search_fields = ('path', 'hash')

    def _check_file(self):
        return super()._check_file()  # todo: override with design-specific stuff


class VideoAnalysisModel(NoGetterModel):
    _analyzer: Optional[VideoAnalyzer]  # todo: try to be more VideoAnalyzer-agnostic
    _video: Optional[VideoFileModel]
    _design: Optional[DesignFileModel]

    _table = 'analyses'
    _flex_table = 'analysis_attributes'
    _fields: dict = {
        'id': types.PRIMARY_ID,

        'video': types.FOREIGN_ID,
        'design': types.FOREIGN_ID,
        'results': types.FOREIGN_ID,  # ID of ResultsModel entry

        'analyzer_type': types.STRING,      # type of the analyzer (resolved ~ isimple.core.config.AnalyzerConfig)
        'config': types.STRING,             # configuration (JSON)

        'description': types.STRING,        # description of the analysis
        'added': types.DATE,                # date&time when this analysis was added
        'start_date': types.DATE,           # date&time when this analysis was started
        'finish_date': types.DATE,          # date&time when this analysis was finished
        'elapsed': types.FLOAT,             # duration of analysis (in seconds)
    }

    _search_fields = (
        'description', 'analyzer_type', 'added',
    )

    def __init__(self, *args, **kwargs):
        super().__init__()
        self._analyzer = None
        self._video = None
        self._design = None

    def set_analyzer(self, analyzer: VideoAnalyzer):
        self._analyzer = analyzer

    def store(self, fields = None):
        if self._analyzer is not None:
            # Store analysis setup
            self.update({
                'analyzer_type': self._analyzer.__class__.__name__,
                'config': json.dumps(self._analyzer.config.to_dict()),
                'description': self._analyzer.description,
            })

            if self._video is None:
                try:
                    self._video = self._db.add_video_file(self._analyzer.config.video_path, self, '_video')
                except ValueError:
                    pass

            if self._design is None:
                try:
                    self._design = self._db.add_design_file(self._analyzer.config.design_path, self, '_design')
                except ValueError:
                    pass

            # Store results
            for k,df in self._analyzer.results.items():
                # Add columns
                model = self._db.add_results()
                model.update({
                    'analysis': self['id'],
                    'feature': k,
                    'data': df.to_json(orient='columns'),
                })
                model.store()
                self.update({
                    'results': model['id']
                })

            # Store timing info
            t = self._analyzer.timing
            if t is not None:
                self.update({
                    'start_date': t.t0,
                    'finish_date': t.t1,
                    'elapsed': t.elapsed,
                })

        super().store(fields)

    def get_latest_config(self) -> dict:  # todo: also: can actually set the config ~ endpoint
        """ todo: queries!
                    ->  self._video.resolve()
                    ->  query History for analyses with self._video['id']
                            if there are no matches, return an empty dict
                            else, take the latest match and continue
                    ->  config = json.loads(match['config'])
                    ->  if self._design is not None:
                            self._design.resolve()
                            config.pop('design_path')
                    -> return config
        """
        return {}

    def commit_files(self):
        self._video.resolve()
        self._video.store()
        self._design.resolve()
        self._design.store()

        self._db.add_roi(
            self._analyzer.transform.config.roi,
            self._video, self._design, self
        )

        self.update({
            'video': self._video['id'],
            'design': self._design['id'],
        })


class History(Database):
    path = settings.db.path

    _models = (VideoAnalysisModel, ResultsModel, VideoFileModel, DesignFileModel, RoiModel)
    _memotable: dict

    def __init__(self, timeout=1.0):
        super().__init__(self.path, timeout)

    def add_analysis(self, analyzer: VideoAnalyzer) -> VideoAnalysisModel:
        model = VideoAnalysisModel()
        model.set_analyzer(analyzer)
        model.add(self)
        model.store()
        return model

    def add_results(self) -> ResultsModel:
        model = ResultsModel()
        model.add(self)
        model.store()
        return model

    def add_video_file(self, path: Optional[str], parent: Model, attribute: str) -> VideoFileModel:
        if path is not None:
            model = VideoFileModel()
            model.add(self)
            model.set_parent(parent, attribute)
            model.queue_hash(path)
            model.store()
            return model
        else:
            raise ValueError

    def add_design_file(self, path: Optional[str], parent: Model, attribute: str) -> DesignFileModel:
        if path is not None:
            model = DesignFileModel()
            model.add(self)
            model.set_parent(parent, attribute)
            model.queue_hash(path)
            model.store()
            return model
        else:
            raise ValueError

    def add_roi(self, roi: Union[np.ndarray, str], video: VideoFileModel, design: DesignFileModel, analysis: VideoAnalysisModel):
        if not isinstance(roi, str):
            roi = ndarray2str(roi)

        model = RoiModel()
        model.update({
            'roi': roi,
            'video': video['id'],
            'design': design['id'],
            'analysis': analysis['id']
        })
        model.add(self)
        model.store()
        analysis.update({'roi': model['id']})
        return model
