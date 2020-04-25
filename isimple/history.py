import os
import abc
import time
import json
from typing import Optional, Tuple, Union, List, Type

from datetime import datetime
import six

import multiprocessing

import numpy as np
import pandas as pd

from isimple import settings, get_logger

from isimple.core import RootException
from isimple.dbcore import Model, Database, types, MatchQuery
from isimple.dbcore.query import InvalidQueryArgumentValueError, InvalidQueryError, NullSort
from isimple.dbcore.queryparse import parse_query_parts, parse_query_string
from isimple.util import hash_file, ndarray2str, str2ndarray
from isimple.config import dumps

from isimple.video import BaseVideoAnalyzer


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
    _hash_q: multiprocessing.Queue
    _parent: Optional[Tuple[Model, str]] # todo: what was this again?

    def __init__(self, *args, path: str = None, **kwargs):
        super().__init__(*args, **kwargs)
        self._parent = None
        if path is not None:
            self.queue_hash(path)

    def queue_hash(self, path: str):
        self._path = path
        self.update({'path': path})
        if self._check_file():
            self._hash_q = hash_file(self._path)
        else:
            raise ValueError
        log.info(f"queueing hash for {path}")

    def _check_file(self):
        return self._check_file_exists()

    def _check_file_exists(self) -> bool:
        if self._path is not None:
            return os.path.isfile(self._path)
        else:
            return False

    def hash(self) -> str:
        try:
            hash = self._hash_q.get()
            return hash
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
        if self._hash_q is not None:
            if self._hash_q.qsize():
                hash = self.hash()
                match = self._db._fetch(self.__class__, MatchQuery('hash', hash))  # todo: is there a cleaner way to do this?

                if any(hash == m['hash'] for m in match):
                    match = match.get()
                    log.debug(f"{hash} -> {match}")
                    self.remove()
                    setattr(*self._parent, match)
                else:
                    log.debug(f"{hash} -> {self}")
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
    _analyzer: Optional[BaseVideoAnalyzer]  # todo: try to be more VideoAnalyzer-agnostic
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

    def get_config(self) -> dict:
        return json.loads(self['config'])

    def set_analyzer(self, analyzer: BaseVideoAnalyzer):
        self._analyzer = analyzer

    def store(self, fields = None):
        if self._analyzer is not None:
            # Store analysis setup
            self.update({
                'analyzer_type': self._analyzer.__class__.__name__,
                'config': json.dumps(self._analyzer.config.to_dict()),
                'description': self._analyzer.description,
            })

            if self._analyzer.config.video_path and self._video is None:
                try:
                    self._video = self._db.add_file(self._analyzer.config.video_path, self, VideoFileModel, '_video')
                except ValueError as e:
                    pass

            if self._analyzer.config.design_path and self._design is None:
                try:
                    self._design = self._db.add_file(self._analyzer.config.design_path, self, DesignFileModel, '_design')
                except ValueError as e:
                    pass

            if self._video is not None and self._design is not None:
                self.commit_files()

            # Store results
            for k,df in self._analyzer.results.items():
                # Add columns
                model = self._db.add_results()  # todo: should have a _results: Dict[ <?>, ResultsModel] so these don't spawn new results each time
                model.update({
                    'analysis': self['id'],
                    'feature': k,
                    'data': df.to_json(orient='columns'),
                })
                model.store()
                self.update({
                    'results': model['id']  # todo: what if a single analyzer produces multiple results?
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

    def commit_files(self):
        if self._video is not None and self._design is not None:
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

    def export(self):
        # todo: should get data from db instead of self._analyzer
        name = str(os.path.splitext(self._analyzer.config.video_path)[0])  # type: ignore
        f = name + ' ' + datetime.now().strftime("%Y-%m-%d %H-%M-%S") + '.xlsx'

        w = pd.ExcelWriter(f)
        for k,v in self._analyzer.results.items():
            v.to_excel(w, sheet_name=k)

        pd.DataFrame([dumps(self._analyzer.config)]).to_excel(w, sheet_name='meta')

        w.save()
        w.close()


class History(Database):
    path = settings.db.path

    _models = (VideoAnalysisModel, ResultsModel, VideoFileModel, DesignFileModel, RoiModel)
    _memotable: dict

    def __init__(self, timeout=1.0):
        super().__init__(self.path, timeout)

    def _fetch(self, model_cls, query=None, sort=None):
        """Returns results of a query string ~ beets syntax
        Taken from beets.library.Library._fetch()
        """

        # Parse the query, if necessary.
        try:
            parsed_sort = None
            if isinstance(query, six.string_types):
                query, parsed_sort = parse_query_string(query, model_cls)
            elif isinstance(query, (list, tuple)):
                query, parsed_sort = parse_query_parts(query, model_cls)
        except InvalidQueryArgumentValueError as exc:
            raise InvalidQueryError(query, exc)

        # Any non-null sort specified by the parsed query overrides the
        # provided sort.
        if parsed_sort and not isinstance(parsed_sort, NullSort):
            sort = parsed_sort
        else:
            sort = None

        return super(History, self)._fetch(model_cls, query, sort)

    def get_latest_analyses(self, N: int = 10) -> List[VideoAnalysisModel]:
        models: List[VideoAnalysisModel] = []
        for vam in self._fetch(VideoAnalysisModel, "added-"):
            if vam['config'] and vam['video'] is not None and vam['design'] is not None:  # todo: check ~ can_launch & replace field checks with correct query
                models.append(vam)
            if len(models) >= N:
                break

        return models

    def get_video_config(self, video_path: str) -> dict:
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
        raise NotImplementedError

    def add_analysis(self, analyzer: BaseVideoAnalyzer) -> VideoAnalysisModel:
        model = VideoAnalysisModel()
        model.set_analyzer(analyzer)
        model.add(self)
        analyzer.set_model(model)

        return model

    def add_file(self, path: Optional[str], parent: Model, filetype: Type[FileModel], attribute: str) -> FileModel:
        if path is not None:
            model = filetype(path = path)
            model.add(self)
            model.set_parent(parent, attribute)  # todo: not super clear how _parent = (parent, attribute) works...
            model.store()
            return model
        else:
            raise ValueError

    def add_results(self) -> ResultsModel:
        model = ResultsModel()
        model.add(self)
        model.store()
        return model

    def add_roi(self, roi: dict, video: VideoFileModel, design: DesignFileModel, analysis: VideoAnalysisModel):
        roi = json.dumps(roi)

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
