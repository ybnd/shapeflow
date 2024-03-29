import os
import json
from typing import Optional, Tuple, List, Dict, Type
from pathlib import Path
import datetime
import sqlite3

from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy import create_engine, Column, Integer, Float, String, DateTime, ForeignKey

import pandas as pd

from shapeflow.api import api
from shapeflow.core import RootInstance
from shapeflow.core.db import Base, DbModel, SessionWrapper, FileModel, BaseAnalysisModel
from shapeflow import settings, get_logger, ResultSaveMode
from shapeflow.core.config import __meta_sheet__
from shapeflow.config import normalize_config, VideoAnalyzerConfig
from shapeflow.core.streaming import EventStreamer

from shapeflow.core.backend import BaseAnalyzer, BaseAnalyzerConfig


log = get_logger(__name__)


class VideoFileModel(FileModel):
    """Database model of a video file.
    """
    __tablename__ = 'video_file'

    def resolve(self) -> 'VideoFileModel':
        video = super().resolve()
        assert isinstance(video, VideoFileModel)
        return video


class DesignFileModel(FileModel):
    """Database model of a design file.
    """
    __tablename__ = 'design_file'

    def resolve(self) -> 'DesignFileModel':
        design = super().resolve()
        assert isinstance(design, DesignFileModel)
        return design


class ConfigModel(DbModel):
    """Database model of a configuration.
    """
    __tablename__ = 'config'

    id = Column(Integer, primary_key=True)

    video = Column(Integer, ForeignKey('video_file.id'))
    design = Column(Integer, ForeignKey('design_file.id'))
    analysis = Column(Integer, ForeignKey('analysis.id'))

    json = Column(String)

    added = Column(DateTime)


class ResultModel(DbModel):
    """Database model of a result.
    """
    __tablename__ = 'results'

    id = Column(Integer, primary_key=True)

    analysis = Column(Integer, ForeignKey('analysis.id'))
    run = Column(Integer)
    config = Column(Integer, ForeignKey('config.id'))

    feature = Column(String)
    """The feature that was analyzed"""
    data = Column(String)
    """Results of the analysis. 
    In JSON, formatted ~ ``pandas.DataFrame.to_json(orient='split')``"""

    started = Column(DateTime)
    finished = Column(DateTime)
    elapsed = Column(Float)


class AnalysisModel(BaseAnalysisModel):
    """Database model of an analysis.

    Contains a reference to a
    :class:`~shapeflow.core.backend.BaseAnalyzer` instance.
    """
    __tablename__ = 'analysis'

    _analyzer: Optional[BaseAnalyzer]
    _video: Optional[VideoFileModel]
    _design: Optional[DesignFileModel]
    _config: Optional[ConfigModel]
    _added_by_context: Dict[str, datetime.datetime]

    id = Column(Integer, primary_key=True)
    runs = Column(Integer)

    video = Column(Integer, ForeignKey('video_file.id'))
    design = Column(Integer, ForeignKey('design_file.id'))
    config = Column(Integer, ForeignKey('config.id'))
    results = Column(Integer, ForeignKey('results.id'))

    name = Column(String)
    description = Column(String)

    added = Column(DateTime)
    modified = Column(DateTime)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._resolve_attributes()

    def _resolve_attributes(self):
        for attr in ['_analyzer', '_video', '_design', '_config']:
            if not hasattr(self, attr):
                setattr(self, attr, None)

    def get_name(self) -> str:
        """
        Returns
        -------
        str
            Name of the analysis from the database.
            Empty names are reset to '#{id}'
        """
        with self.session(add=False):
            if self.name is None:
                self.name = f"#{self.id}"
            return self.name

    def get_runs(self) -> int:
        """
        Returns
        -------
        int
            Number of completed runs for the analysis
        """
        with self.session(add=False):
            if self.runs is None:
                self.runs = 0
            return self.runs

    def get_id(self) -> int:
        """
        Returns
        -------
        int
            The database id of the analysis
        """
        with self.session(add=False):
            return self.id

    def _set_analyzer(self, analyzer: BaseAnalyzer):
        self._analyzer = analyzer

    def _add_video(self, path: str) -> VideoFileModel:
        model = VideoFileModel(path=path)
        model.connect(self)

        return model

    def _add_design(self, path: str) -> DesignFileModel:
        model = DesignFileModel(path=path)
        model.connect(self)

        return model

    def _resolve_files(self):
        if self._analyzer.config.video_path and (
                self._video is None or self._video.get('path') != self._analyzer.config.video_path):
            try:
                self._video = self._add_video(
                    path=self._analyzer.config.video_path)
            except ValueError as e:
                pass

        if self._analyzer.config.design_path and (
                self._design is None or self._design.get('path') != self._analyzer.config.design_path):
            try:
                self._design = self._add_design(
                    path=self._analyzer.config.design_path)
            except ValueError as e:
                pass

        if self._video is not None:
            self._video = self._video.resolve()

        if self._design is not None:
            self._design = self._design.resolve()

        with self.session() as s:
            if self._video is not None:
                self.video = self._video.id
            if self._design is not None:
                self.design = self._design.id

    def _add_config(self, json: str) -> Optional[ConfigModel]:
        with self.session():
            video = self.video
            design = self.design
            analysis = self.id

        if video is not None or design is not None:
            model = ConfigModel(
                video=video, design=design, analysis=analysis,
                json=json,
                added=datetime.datetime.now(),
            )
            model.connect(self)
            return model
        else:
            return None

    def store(self):  # todo: consider passing analyzer to store() instead of keeping a reference
        """Store analysis information from the
        :class:`~shapeflow.core.backend.BaseAnalyzer` to the database.
        """
        self._resolve_attributes()
        if self._analyzer is not None:
            config_json = json.dumps(self._analyzer.get_config(do_tag=True))
            self._resolve_files()

            if self._config is None:
                self._config = self._add_config(json=config_json)
            else:
                if config_json != self._config.get('json'):
                    self._config = self._add_config(json=config_json)

            with self.session() as s:
                if self._analyzer.config.name is not None:
                    if not self._analyzer.config.name.strip():
                        self._analyzer.config.name = f"#{self.id}"
                    else:
                        self.name = self._analyzer.config.name.strip()
                        self._analyzer.config.name = self.name
                if self._analyzer.config.description is not None:
                    self.description = self._analyzer.config.description

                self.runs = self._analyzer.runs

                s.commit()

                if self._config is not None:
                    self.config = self._config.id

                # Store results
                for k, df in self._analyzer.results.items():
                    # Add columnsfe
                    if not df.isnull().all().all():  # todo: doesn't save results if there's *one* NaN?
                        model = ResultModel(
                            analysis=self.id,
                            run=self.runs,
                            config=self.config,
                            feature=k,
                            data=df.to_json(orient='split'),
                        )  # todo: should have a _results: Dict[ <?>, ResultsModel] so these don't spawn new results each time
                        s.add(model)

                        # Store timing info
                        t = self._analyzer.timing
                        if t is not None:
                            model.started = datetime.datetime.fromtimestamp(t.t0)
                            model.finished = datetime.datetime.fromtimestamp(t.t1)
                            model.elapsed = t.elapsed

                        s.commit()
                        self.results = model.id

    def export_result(self, run: int = None, manual: bool = False):
        """Export a result to disk

        Parameters
        ----------
        run : int
            The run to export
        manual : bool
            Whether this export request is manual (i.e. explicitly requested
            by the user). This setting determines whether to follow
            ``settings.app.save_result_manual`` or ``settings.app.save_result_auto``
            when choosing where or whether to actually save.
        """
        with self.session() as s:
            if self.runs is None or self.runs < 1:
                raise ValueError(f"'{self}' has no runs to export!")

            # If no run specified, export the latest
            if run is None:
                run = self.runs

            results = list(
                s.query(ResultModel).filter_by(analysis=self.id).filter_by(run=run)
            )
            config = json.loads(
                s.query(ConfigModel).filter_by(id=results[0].config).first().json
            )
            video = s.query(VideoFileModel).filter_by(id=self.video).first()
            design = s.query(DesignFileModel).filter_by(id=self.design).first()

            base_f = None

            if manual:
                if settings.app.save_result_manual == ResultSaveMode.next_to_video:
                    base_f = str(os.path.splitext(config['video_path'])[0])
                elif settings.app.save_result_manual == ResultSaveMode.next_to_design:
                    base_f = str(os.path.splitext(config['design_path'])[0])
                elif settings.app.save_result_manual == ResultSaveMode.directory:
                    base_f = os.path.join(
                        str(settings.app.result_dir),
                        f"{self.name} run {run}"
                    )
            else:
                if settings.app.save_result_auto == ResultSaveMode.next_to_video:
                    base_f = str(os.path.splitext(config['video_path'])[0])
                elif settings.app.save_result_auto == ResultSaveMode.next_to_design:
                    base_f = str(os.path.splitext(config['design_path'])[0])
                elif settings.app.save_result_auto == ResultSaveMode.directory:
                    base_f = os.path.join(
                        str(settings.app.result_dir),
                        f"{self.name} run {run}"
                    )

            if base_f is not None:
                f = base_f + ' ' + datetime.datetime.now().strftime(
                    settings.format.datetime_format_fs
                ) + '.xlsx'

                w = pd.ExcelWriter(f)

                # Features to separate sheets
                for result in results:
                    df = pd.read_json(result.data, orient='split')
                    df.to_excel(w, sheet_name=result.feature)

                # Metadata in a separate sheet
                pd.DataFrame([json.dumps({
                    'config': config,
                    'video_hash': video.hash,
                    'design_hash': design.hash,
                }, indent=2)]).to_excel(
                    w, sheet_name=__meta_sheet__
                )

                w.save()
                w.close()
                log.info(f"'{self.id}' results exported to {f}")
            else:
                log.warning(f"'{self.id}' results were not exported!")


    def load_config(self, video_path: str = None, design_path: str = None, include: List[str] = None) -> Optional[dict]:
        """Load configuration from the database.

        Parameters
        ----------
        video_path : str
            Path to video file
        design_path : str
            Path to design file
        include : List[str]
            List of fields which must be included in the configuration. If a
            matching ConfigModel doesn't provide all of these, the
            other matches will be parsed to complete it.

        Returns
        -------
        dict
            Configuration dict, if a matching config is found. Otherwise,
            returns ``None``

        """
        if include is None:
            include = ['transform', 'masks']

        # Check whether all fields in include are valid
        for field in include:
            assert field in VideoAnalyzerConfig.__fields__, \
                f"'{field}' in `include` is not a `VideoAnalyzerConfig` field."

        if video_path is not None:
            self._video = self._add_video(path=video_path)

        if design_path is not None:
            self._design = self._add_design(path=design_path)

        if self._video is not None:
            self._video = self._video.resolve()
            if self._design is not None:
                self._design = self._design.resolve()

            # Query for latest usages of video.id & design.id)
            with self.session() as s:
                q = s.query(ConfigModel)
                q = q.filter(ConfigModel.video == self._video.id)
                if self._design is not None:
                    q = q.filter(ConfigModel.design == self._design.id)
                q = q.filter(ConfigModel.analysis != self.id)

                config = {}
                for match in q.order_by(ConfigModel.id.desc()):
                    match_config = normalize_config(json.loads(match.json))

                    # Assimilate `include` fields from match
                    for field in include:
                        if field in match_config:
                            config[field] = match_config[field]

                    # Check if enough info in ìncluded config
                    ok = []
                    if 'transform' in config and 'transform' in include:
                        # 'transform' field should contain ROI
                        if 'roi' in config['transform']:
                            if config['transform']['roi'] is not {}:
                                ok.append(True)
                                include.remove('transform')
                    if 'masks' in config and 'masks' in include:
                        # 'masks' field should not be empty
                        if len(config['masks']) > 0:
                            ok.append(True)
                            include.remove('masks')

                    if len(ok) > 0 and all(ok):
                        break
            return config
        else:
            return None

    def get_config_json(self) -> Optional[str]:
        with self.session() as s:
            return s.query(ConfigModel.json).\
                    filter(ConfigModel.id == self.config).first()[0]  # todo: why does it return a tuple of length 1?

    def _fetch_latest_config(self) -> Optional[ConfigModel]:
        with self.session() as s:
            return s.query(ConfigModel). \
                order_by(ConfigModel.added.desc()). \
                first()  # todo: check if ordering by datetime works properly

    def _added(self, context: str = None) -> datetime.datetime:
        if self._config is None:
            self._config = self._fetch_latest_config()
        if not hasattr(self, '_added_by_context'):
            self._added_by_context = {}

        with self.session() as s:
            if context not in self._added_by_context:
                if self._config is not None:
                    assert isinstance(self._config.added, datetime.datetime)
                    return self._config.added
                else:
                    assert isinstance(self.added, datetime.datetime)
                    return self.added
            else:
                return self._added_by_context[context]

    def _step_config(self, filter, order, context: str = None) -> Tuple[Optional[dict], Optional[int]]:
        with self.session() as s:
            q = list(
                s.query(ConfigModel).\
                filter(ConfigModel.video == self.video).\
                filter(ConfigModel.design == self.design).\
                filter(filter).\
                order_by(order)
            )

            for match in q:
                assert isinstance(match, ConfigModel)
                assert isinstance(match.json, str)  # todo: fail more gracefully if json is empty; skip & remove from database
                config = normalize_config(json.loads(match.json))

                if context is None:
                    self._config = match
                    self._config.connect(self)
                    s.add(self._config)
                    return config, match.id
                else:
                    assert self._analyzer is not None
                    if context in config and config[context] != self._analyzer.get_config()[context]:
                        self._config = None
                        assert isinstance(match.added, datetime.datetime)
                        self._added_by_context[context] = match.added
                        return {context: config[context]}, match.id
        return None, None

    def get_undo_config(self, context: str = None) -> Tuple[Optional[dict], Optional[int]]:
        """Undo configuration. If a ``context`` is supplied, ensure that the
        ``context`` field changes, but the other fields remain the same

        Parameters
        ----------
        context : str
            Name of a ``VideoAnalyzerConfig`` field

        Raises
        ------
        ValueError
            If ``context`` is not a ``VideoAnalyzer`` field
        """
        if context is None or context in VideoAnalyzerConfig.__fields__:
            return self._step_config(
                ConfigModel.added < self._added(context),
                ConfigModel.added.desc(),
                context
            )
        else:
            raise ValueError(f"Invalid undo context '{context}'")

    def get_redo_config(self, context: str = None) -> Tuple[Optional[dict], Optional[int]]:
        """Redo configuration. If a ``context`` is supplied, ensure that the
        ``context`` field changes, but the other fields remain the same

        Parameters
        ----------
        context : str
            Name of a ``VideoAnalyzerConfig`` field

        Raises
        ------
        ValueError
            If ``context`` is not a ``VideoAnalyzer`` field
        """
        if context is None or context in VideoAnalyzerConfig.__fields__:
            return self._step_config(
                ConfigModel.added > self._added(context),
                ConfigModel.added,
                context
            )
        else:
            raise ValueError(f"Invalid redo context '{context}'")

class History(SessionWrapper, RootInstance):
    """Interface to the history database
    """
    _eventstreamer: EventStreamer

    def __init__(self, path: Path = None):
        super().__init__()

        if path is None:
            path = Path(str(settings.db.path))

        self._engine = create_engine(f'sqlite:///{str(path)}')
        try:
            Base.metadata.create_all(self._engine)
        except sqlite3.OperationalError as e:
            if "already exists" in str(e):
                pass
            else:
                log.error(f"could not create tables - {e.__class__.__name__}: {str(e)}")
        self._session_factory = scoped_session(sessionmaker(bind=self._engine))

    def set_eventstreamer(self, eventstreamer: EventStreamer):
        self._eventstreamer = eventstreamer

    def notice(self, message: str, persist: bool = False):
        self._eventstreamer.event(
            'notice', id='', data={'message': message, 'persist': persist}
        )

    def add_video_file(self, path: str) -> VideoFileModel:
        """Add a video file to the database.
        Duplicate files are resolved to their original entry.

        Parameters
        ----------
        path : str
            The path of the file to add

        Returns
        -------
        VideoFileModel
            A database model of the file. Will reference the original entry
            if the user tried to add a previously used file again.
        """
        file = VideoFileModel(path=path)
        file.connect(self)
        file.resolve()
        return file

    def add_design_file(self, path: str) -> DesignFileModel:
        """Add a design file to the database.
        Duplicate files are resolved to their original entry.

        Parameters
        ----------
        path : str
            The path of the file to add

        Returns
        -------
        DesignFileModel
            A database model of the file. Will reference the original entry
            if the user tried to add a previously used file again.
        """
        file = DesignFileModel(path=path)
        file.connect(self)
        file.resolve()
        return file

    def add_analysis(self, analyzer: BaseAnalyzer, model: AnalysisModel = None) -> AnalysisModel:
        """Add a new analysis to the database.

        Parameters
        ----------
        analyzer : BaseAnalyzer
            The analyzer object to add to the database
        model : AnalysisModel
            Optionally, an existing model can be specified.
            Defaults to ``None``

        Returns
        -------
        AnalysisModel
            If a ``model`` is provided, no new :class:`~AnalysisModel`
            will be created and the ``analyzer`` will be linked to the
            existing ``model`` instead.
        """
        if model is None:
            with self.session() as s:
                model = AnalysisModel()
                s.add(model)
        model.connect(self)

        model._set_analyzer(analyzer)
        analyzer.set_model(model)
        return model

    def fetch_analysis(self, id: int) -> Optional[AnalysisModel]:
        """Fetch an analysis model from the database.

        Parameters
        ----------
        id : int
            Database id of the analysis to fetch
        """
        with self.session() as s:
            return s.query(AnalysisModel).filter(AnalysisModel.id == id).\
                first()

    # @history.expose(history.get_recent_paths)
    @api.db.get_recent_paths.expose()
    def get_paths(self) -> Dict[str, List[str]]:
        """Fetch the latest video and design file paths from the
        database.

        :attr:`shapeflow.api._DatabaseDispatcher.get_recent_paths`

        Number of paths is limited by ``settings.app.recent_files``
        """
        with self.session() as s:
            return {
                'video_path': [r[0] for r in s.query(VideoFileModel.path).\
                    order_by(VideoFileModel.used.desc()).\
                    limit(settings.app.recent_files).all()],
                'design_path': [r[0] for r in s.query(DesignFileModel.path). \
                    order_by(DesignFileModel.used.desc()). \
                    limit(settings.app.recent_files).all()]
            }

    # @history.expose(history.get_result_list)
    @api.db.get_result_list.expose()
    def get_result_list(self, analysis: int) -> dict:
        """Fetch the result list for a given analysis

        :attr:`shapeflow.api._DatabaseDispatcher.get_result_list`

        Parameters
        ----------
        analysis : int
            Database id of the analysis

        Returns
        -------
        dict
            A ``dict`` mapping run id ``int`` to result id ``int``
        """
        with self.session() as s:
            runs = s.query(AnalysisModel).\
                filter(AnalysisModel.id == analysis).first().runs

            return {
                run: s.query(ResultModel).\
                    filter(ResultModel.analysis == analysis).\
                    filter(ResultModel.run == run).first().finished
                for run in range(1, runs+1)
            }

    # @history.expose(history.get_result)
    @api.db.get_result.expose()
    def get_result(self, analysis: int, run: int) -> dict:
        """Fetch the result for a given analysis and run

        :attr:`shapeflow.api._DatabaseDispatcher.get_result`

        Parameters
        ----------
        analysis : int
            Database id of the analysis
        run : int
            Run number of the result to fetch

        Returns
        -------
        dict
            Analysis results, as a ``dict`` formatted ~
            ``pandas.DataFrame.to_json(orient='split')``
        """
        with self.session() as s:
            return {
                r.feature: json.loads(r.data)
                for r in s.query(ResultModel).\
                    filter(ResultModel.analysis == analysis).\
                    filter(ResultModel.run == run)
            }

    # @history.expose(history.export_result)
    @api.db.export_result.expose()
    def export_result(self, analysis: int, run: int = None) -> bool:
        """Export the result for a given analysis and run

        :attr:`shapeflow.api._DatabaseDispatcher.export_result`

        Parameters
        ----------
        analysis : int
            Database id of the analysis
        run : int
            Run number of the result to fetch

        Returns
        -------
        bool
            ``True`` if exported,
            ``False`` if something went wrong.
        """
        with self.session() as s:
            try:
                a = s.query(AnalysisModel).filter_by(
                    id=analysis
                ).first()
                a.connect(self)
                a.export_result(run=run, manual=True)
                return True
            except Exception as e:
                log.error(f"{e.__class__.__name__}: {e}")
                self.notice(
                    f"could not export analysis '{analysis}' run '{run}'"
                )
                return False

    def check(self) -> bool:
        """Check the database's integrity (somewhat).
        Makes sure that the required tables exist and that their columns match.

        Returns
        -------
        bool
            ``True`` if everything's fine,
            ``False`` if the database is messed up
        """
        log.debug('checking history')

        ok = []
        models = [
            VideoFileModel, DesignFileModel, ConfigModel,
            ResultModel, AnalysisModel
        ]

        with self.session() as s:
            db = s.bind.connect()
            cursor = db.connection.cursor()

            cursor.execute(
                "SELECT name FROM sqlite_master WHERE type='table';")
            tables = [name[0] for name in cursor.fetchall()]

            for model in models:
                table = model.__tablename__  # type: ignore

                if table in tables:
                    ok.append(True)
                else:
                    log.warning(f"table '{table}' is missing from the database.")
                    ok.append(False)

                cursor.execute(f"PRAGMA table_info({table})")
                columns = {column[1]: column[2] for column in
                           cursor.fetchall()}

                model_columns = {
                    column.name: str(column.type) for column in
                    model.__table__.columns  # type: ignore
                }

                if columns == model_columns:
                    ok.append(True)
                else:
                    log.warning(f"table '{table}' columns don't match.")
                    ok.append(False)

            db.close()

        return all(ok)


    # @history.expose(history.clean)
    @api.db.clean.expose()
    def clean(self) -> None:
        """Clean the database.

        :attr:`shapeflow.api._DatabaseDispatcher.clean`

        * remove 'video_file & 'design_file' entries with <null> path

           * resolve entries with ``<null>`` hash

        * remove 'analysis' entries with ``<null>`` config

        * remove 'config' entries with ``<null>`` json

        * for 'analysis' entries older than ``settings.db.cleanup_interval``

           * remove all non-primary 'config' entries

           * remove all non-primary 'results' entries


        """
        log.debug(f"cleaning history")
        threshold = datetime.datetime.now() - datetime.timedelta(
            days=settings.db.cleanup_interval
        )

        with self.session() as s:
            s.query(VideoFileModel).filter_by(path=None).delete()
            s.query(DesignFileModel).filter_by(path=None).delete()

            unhashed = list(s.query(VideoFileModel).filter_by(hash=None)) \
                       + list(s.query(DesignFileModel).filter_by(hash=None))

            for f in unhashed:
                f._queue_hash(f.path)

            s.query(ConfigModel).filter_by(json=None).delete()
            s.query(AnalysisModel).filter_by(config=None).delete()

            for old in s.query(AnalysisModel).\
                    filter(AnalysisModel.modified < threshold):
                s.query(ConfigModel). \
                    filter(ConfigModel.analysis == old.id). \
                    filter(ConfigModel.id != old.config).delete()

                s.query(ResultModel). \
                    filter(ResultModel.analysis == old.id). \
                    filter(ResultModel.id != old.results).delete()

            for f in unhashed:
                f.connect(self)
                f.resolve()


    # @history.expose(history.forget)
    @api.db.forget.expose()
    def forget(self) -> None:
        """Remove everything.

        :attr:`shapeflow.api._DatabaseDispatcher.forget`
        """
        log.info(f"clearing history")
        models = [
            AnalysisModel,
            VideoFileModel,
            DesignFileModel,
            ConfigModel,
            ResultModel
        ]

        with self.session() as s:
            for model in models:
                s.query(model).delete()



