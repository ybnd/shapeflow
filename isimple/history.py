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
from isimple.config import dumps, normalize_config

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

        'start_date': types.DATE,
        'finish_date': types.DATE,
        'elapsed': types.FLOAT,
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
        if not self._hash_q.qsize():
            log.debug(f"queueing hash for {path}")

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

    def resolve(self) -> Optional[int]:
        """Check this file's hash against the database; if the file is already
            listed, remove it from the database and set the parent's file to
            the matching file instead.
        """
        if hasattr(self, '_hash_q'):
            if self._hash_q.qsize():
                hash = self.hash()
                match = self._db._fetch(self.__class__, MatchQuery('hash', hash))  # todo: is there a cleaner way to do this?

                if any(hash == m['hash'] for m in match):
                    match = match.get()
                    log.debug(f"file {hash} -> {match}")
                    self.remove()
                    if self._parent is not None:
                        setattr(*self._parent, match)
                    return match['id']
                else:
                    log.debug(f"file {hash} -> {self}")
                    self.update({
                        'path': self._path,
                        'hash': hash,
                    })
                    return self['id']
            else:
                return None
        else:
            return self['id']

    def join(self):
        if not self['hash']:
            if self._hash_q is not None:
                while not self._hash_q.qsize():
                    time.sleep(0.01)


class ConfigModel(NoGetterModel):
    _table = 'configs'
    _flex_table = 'config_attributes'
    _fields: dict = {
        'id': types.PRIMARY_ID,

        'video': types.FOREIGN_ID,
        'design': types.FOREIGN_ID,
        'analysis': types.FOREIGN_ID,

        'json': types.STRING,             # configuration (JSON)

        'added': types.DATE,
        'modified': types.DATE,
    }

    def store(self, fields=None):
        self['modified'] = time.time()
        super().store()

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
    _config: Optional[ConfigModel]

    _table = 'analyses'
    _flex_table = 'analysis_attributes'
    _fields: dict = {
        'id': types.PRIMARY_ID,

        'video': types.FOREIGN_ID,
        'design': types.FOREIGN_ID,
        'config': types.FOREIGN_ID,
        'results': types.FOREIGN_ID,  # ID of ResultsModel entry

        'analyzer_type': types.STRING,      # type of the analyzer (resolved ~ isimple.core.config.AnalyzerConfig)

        'description': types.STRING,        # description of the analysis
        'added': types.DATE,                # date&time when this analysis was added
        'modified': types.DATE,             # date&time when this analysis was last modified
    }

    _search_fields = (
        'description', 'analyzer_type', 'added',
    )

    def __init__(self, *args, **kwargs):
        super().__init__()
        self._analyzer = None
        self._video = None
        self._design = None
        self._config = None

    def set_analyzer(self, analyzer: BaseVideoAnalyzer):
        self._analyzer = analyzer

    def get_config_by_video(self) -> dict:
        if self._video is not None:
            self._video.resolve()
            if self._design is not None:
                self._design.resolve()
                return self._db.get_config(self._video, self._design)
            return self._db.get_config(self._video)
        else:
            return {}

    def store(self, fields = None):
        if self._analyzer is not None:
            # Store analysis setup
            self.update({
                'analyzer_type': self._analyzer.__class__.__name__,
                'description': self._analyzer.description,
            })

            if self._analyzer.config.video_path and (self._video is None or self._video['path'] != self._analyzer.config.video_path):
                try:
                    self._video = self._db.add_file(self._analyzer.config.video_path, VideoFileModel, self, '_video')
                except ValueError as e:
                    pass

            if self._analyzer.config.design_path and (self._design is None or self._design['path'] != self._analyzer.config.design_path):
                try:
                    self._design = self._db.add_file(
                        self._analyzer.config.design_path, DesignFileModel, self, '_design')
                except ValueError as e:
                    pass

            if self._video is not None and self._design is not None:
                self.commit_files()

            # Store config
            self._db.add_config(self._analyzer.get_config(do_tag=True), self, self._video, self._design)

            # Store results
            for k, df in self._analyzer.results.items():
                # Add columnsfe
                if not df.isnull().all().all():
                    model = self._db.add_results()  # todo: should have a _results: Dict[ <?>, ResultsModel] so these don't spawn new results each time
                    model.update({
                        'analysis': self['id'],
                        'feature': k,
                        'data': df.to_json(orient='split'),
                    })
                    # Store timing info
                    t = self._analyzer.timing
                    if t is not None:
                        model.update({
                            'start_date': t.t0,
                            'finish_date': t.t1,
                            'elapsed': t.elapsed,
                        })

                    model.store()
                    self.update({
                        'results': model['id']  # todo: what if a single analyzer produces multiple results?
                    })
                    # self._analyzer._new_results()

        self['modified'] = time.time()
        super().store(fields)

    def commit_files(self):
        if self._video is not None and self._design is not None:
            self._video.resolve()
            self._video.store()
            self._design.resolve()
            self._design.store()

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

    @property
    def config(self):
        if self._config is None and self['config'] is not None:
            self._config = self._db.fetch_config(self['config'])

        return self._config['json'] if self._config is not None else '{}'


class History(Database):
    path = settings.db.path

    _models = (VideoAnalysisModel, ResultsModel, VideoFileModel, DesignFileModel, ConfigModel)
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

    def get_config(self, analysis: VideoAnalysisModel, video: FileModel, design: FileModel = None, include: List[str] = None) -> dict:
        config = {}
        if include is None:
            include = ['video', 'design', 'transform', 'masks']  # todo: how to handle feature parameters?

        # Query history for latest usages of current video
        # (not including the curent analysis)
        analysis_id = analysis['id']
        video.join()
        video_id = video.resolve()
        q = f"added- ^analysis:{analysis_id} video:{video_id}"  # todo query negation doesn't work for some reason

        if design is not None:
            # Also match design
            design.join()
            design_id = design.resolve()
            q += f" design:{design_id}"
        else:
            # Also grab design file
            include = ['design_path'] + include

        for match in self._fetch(ConfigModel, q):
            # Don't return own config
            if match['analysis'] != analysis_id:
                if match['json'] is not None:
                    match_config = normalize_config(json.loads(match['json']))

                    # Assimilate `include` fields from match
                    for field in include:
                        if field in match_config:
                            config[field] = match_config[field]

                    # Check if enough
                    ok = []
                    if 'transform' in config:
                        if 'roi' in config['transform']:
                            if config['transform']['roi'] is not {}:
                                ok.append(True)
                                include.remove('transform')
                    if 'masks' in config:
                        if len(config['masks']) > 0:
                            ok.append(True)
                            include.remove('masks')

                    if len(ok) > 0 and all(ok):
                        break

        return config

    def get_config_buffer(self, analysis: VideoAnalysisModel, next: bool = False) -> Optional[dict]:
        """For a given VideoAnalysisModel, get the previous or next config
        """
        if analysis._config is None:
            analysis._config = self._fetch(
                ConfigModel,
                f"analysis:{analysis} added-"
            )[0]

        # Query must be performed with formatted timestamp string
        modified = datetime.fromtimestamp(
            analysis._config['modified']
        ).strftime('%Y-%m-%dT%H:%M:%S')

        if next:
            q = f"video:{analysis['video']} design:{analysis['design']} " \
                f"modified:{modified}.. modified+"
        else:
            q = f"video:{analysis['video']} design:{analysis['design']} " \
                f"modified:..{modified} modified-"
        for match in self._fetch(ConfigModel, q):
            # Make sure not to return the same ROI
            if match['id'] != analysis._config['id']:
                if match['json'] != analysis._config['json']:
                    return normalize_config(json.loads(match['json']))

        # If no other options, return None
        return None

    def add_analysis(self, analyzer: BaseVideoAnalyzer, model: VideoAnalysisModel = None) -> VideoAnalysisModel:
        if model is None:
            model = VideoAnalysisModel()
            model.add(self)
        model.set_analyzer(analyzer)
        analyzer.set_model(model)

        return model

    def fetch_analysis(self, id: int) -> Optional[VideoAnalysisModel]:
        try:
            model = self._fetch(VideoAnalysisModel, f"id:{id}")[0]
            model._db = self
            return model
        except IndexError:
            return None

    def fetch_config(self, id: int) -> Optional[ConfigModel]:
        try:
            model = self._fetch(ConfigModel, f"id:{id}")[0]
            model._db = self
            return model
        except IndexError:
            return None

    def fetch_recent_paths(self, model: Type[FileModel]) -> List[str]:
        files = self._fetch(model, 'added-')
        paths = []
        for i, file in enumerate(files):
            if i < settings.app.recent_files:
                paths.append(file['path'])
            else:
                break
        return paths

    def add_file(self, path: Optional[str], filetype: Type[FileModel], parent: Model = None, attribute: str = None) -> FileModel:
        if path is not None:
            model = filetype(path = path)
            model.add(self)
            if parent is not None and attribute is not None:
                model.set_parent(parent, attribute)  # todo: add documentation to _parent
            model.store()
            return model
        else:
            raise ValueError

    def add_results(self) -> ResultsModel:
        model = ResultsModel()
        model.add(self)
        model.store()
        return model

    def add_config(self, config: dict,  analysis: VideoAnalysisModel, video: VideoFileModel = None, design: DesignFileModel = None) -> ConfigModel:
        config_json = json.dumps(config)

        # Return existing entry if the exact same config ~ analysis exists already
        q = f"analysis:{analysis['id']} json:'{config_json}'"

        match = self._fetch(ConfigModel, q)
        if len(match) > 0:
            model = match[0]
            # Update ROI entry
            model['added'] = time.time()
        else:
            # Add a new ROI entry
            model = ConfigModel()
            model.update({
                'json': config_json,
                'video': video['id'] if video is not None else None,
                'design': design['id'] if design is not None else None,
                'analysis': analysis['id']
            })
            model.add(self)
            model.store()

        analysis.update({'config': model['id']})
        analysis._config = model
        return model

    def clean(self, deep: bool = False):
        """Remove all incomplete entries
            * VideoAnalysisModel:
                - missing 'video' & 'design'
            * FileModel:
                - missing 'hash'
            * RoiModel:
                - missing 'roi'
                - 100% duplicates (deep)
            * ResultsModel:
                - missing 'data'
                - 'data' where everythin is NaN (deep)

            & convert legacy JSON strings
                - VideoAnalysisModel['config'] (deep)
                - RoiModel['roi']
        """
        raise NotImplementedError
