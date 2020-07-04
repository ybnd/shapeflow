import json
from typing import Optional, Tuple, List, Dict, Type
from pathlib import Path
import datetime

from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy import create_engine, Column, Integer, Float, String, DateTime, ForeignKey

from isimple.core.db import Base, DbModel, SessionWrapper, FileModel, BaseAnalysisModel
from isimple import Settings, settings, get_logger
from isimple.config import normalize_config

from isimple.core.backend import BaseVideoAnalyzer, BaseAnalyzerConfig


log = get_logger(__name__)


class VideoFileModel(FileModel):
    __tablename__ = 'video_file'

    def resolve(self) -> 'VideoFileModel':
        video = super().resolve()
        assert isinstance(video, VideoFileModel)
        return video


class DesignFileModel(FileModel):
    __tablename__ = 'design_file'

    def resolve(self) -> 'DesignFileModel':
        design = super().resolve()
        assert isinstance(design, DesignFileModel)
        return design


class ConfigModel(DbModel):
    __tablename__ = 'config'

    id = Column(Integer, primary_key=True)

    video = Column(Integer, ForeignKey('video_file.id'))
    design = Column(Integer, ForeignKey('design_file.id'))
    analysis = Column(Integer, ForeignKey('analysis.id'))

    json = Column(String)

    added = Column(DateTime)
    modified = Column(DateTime)


class ResultsModel(DbModel):
    __tablename__ = 'results'

    id = Column(Integer, primary_key=True)

    analysis = Column(Integer, ForeignKey('analysis.id'))

    feature = Column(String)
    data = Column(String)

    started = Column(DateTime)
    finished = Column(DateTime)
    elapsed = Column(Float)


class AnalysisModel(BaseAnalysisModel):
    __tablename__ = 'analysis'

    _analyzer: Optional[BaseVideoAnalyzer]
    _video: Optional[VideoFileModel]
    _design: Optional[DesignFileModel]
    _config: Optional[ConfigModel]
    _added_by_context: Dict[str, datetime.datetime]

    id = Column(Integer, primary_key=True)

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
        with self.session() as s:
            if self.name is None:
                self.name = f"#{self.id}"
            return self.name

    def set_analyzer(self, analyzer: BaseVideoAnalyzer):
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
                json = json,
                added=datetime.datetime.now(),
            )
            model.connect(self)
            return model
        else:
            return None

    def store(self):
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

                s.commit()

                if self._config is not None:
                    self.config = self._config.id

                # Store results
                for k, df in self._analyzer.results.items():
                    # Add columnsfe
                    if not df.isnull().all().all():
                        model = ResultsModel(
                            analysis=self.id,
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

    def load_config(self, video_path: str = None, design_path: str = None, include: List[str] = None) -> Optional[dict]:
        if include is None:
            include = ['video', 'design', 'transform', 'masks']  # todo: how to handle feature parameters?

        if video_path is not None:
            self._video = self._add_video(path=video_path)

        if design_path is not None:
            self._design = self._add_design(path=design_path)

        if self._video is not None:
            self._video = self._video.resolve()
            if self._design is not None:
                self._design = self._design.resolve()

            # Query for latest usages of video_hash
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

    def _step_config(self, filter, order, context: str = None) -> Optional[dict]:
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
                    return config
                else:
                    assert self._analyzer is not None
                    if context in config and config[context] != self._analyzer.config.to_dict()[context]:
                        self._config = None
                        assert isinstance(match.added, datetime.datetime)
                        self._added_by_context[context] = match.added
                        return {context: config[context]}
        return None

    def undo_config(self, context: str = None):
        config = self._step_config(
            ConfigModel.added < self._added(context),
            ConfigModel.added.desc(),
            context
        )
        if self._analyzer is not None and config is not None:
            self._analyzer.set_config(config=config, silent=(context is None))

    def redo_config(self, context: str = None):
        config = self._step_config(
            ConfigModel.added > self._added(context),
            ConfigModel.added,
            context
        )
        if self._analyzer is not None and config is not None:
            self._analyzer.set_config(config=config, silent=(context is None))

class History(SessionWrapper):
    def __init__(self, path: Path = None):
        if path is None:
            path = settings.db.path

        self._engine = create_engine(f'sqlite:///{str(path)}')
        Base.metadata.create_all(self._engine)
        self._session_factory = scoped_session(sessionmaker(bind=self._engine))

    def add_video_file(self, path: str):
        file = VideoFileModel(path=path)
        file.connect(self)
        file.resolve()

    def add_design_file(self, path: str):
        file = DesignFileModel(path=path)
        file.connect(self)
        file.resolve()

    def add_analysis(self, analyzer: BaseVideoAnalyzer, model: AnalysisModel = None) -> AnalysisModel:
        if model is None:
            model = AnalysisModel()
        model.connect(self)

        model.set_analyzer(analyzer)
        model.store()

        analyzer.set_model(model)

        return model

    def fetch_analysis(self, id: int) -> Optional[AnalysisModel]:
        with self.session() as s:
            return s.query(AnalysisModel).filter(AnalysisModel.id == id).\
                first()

    def fetch_paths(self) -> Dict[str, list]:
        with self.session() as s:
            return {
                'video_path': [r[0] for r in s.query(VideoFileModel.path).\
                    order_by(VideoFileModel.used.desc()).\
                    limit(settings.app.recent_files).all()],
                'design_path': [r[0] for r in s.query(DesignFileModel.path). \
                    order_by(DesignFileModel.used.desc()). \
                    limit(settings.app.recent_files).all()]
            }
