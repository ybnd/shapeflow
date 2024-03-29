import abc
import queue
import os
import time
from contextlib import contextmanager
from typing import Optional, List, Type, Any, Tuple
import datetime

from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import scoped_session
from sqlalchemy.orm.util import object_state  # type: ignore
from sqlalchemy.sql.schema import Column
from sqlalchemy.sql.sqltypes import Integer, String, DateTime
from sqlalchemy.exc import InvalidRequestError

from shapeflow import get_logger
from shapeflow.core import RootException, RootInstance, Lockable
from shapeflow.util import hash_file

log = get_logger(__name__)
Base = declarative_base()


class SessionWrapper(object):
    """Wrapper object for a ``SQLAlchemy`` session factory.
    """

    _session_factory: scoped_session

    def connect(self, session_wrapper: 'SessionWrapper'):
        """Share the session factory of another ``SessionWrapper`` instance
        """
        self._session_factory = session_wrapper._session_factory

    @contextmanager
    def session(self):
        """
        ``SQLAlchemy`` session context manager.

        Opens a ``SQLAlchemy`` session and commits after the block is done.
        Changes are rolled back if an exception is raised. Usage::

            with self.session() as s:
                # interact with the database here
        """
        session = self._session_factory()
        try:
            yield session
            session.commit()
        except:
            session.rollback()
        finally:
            session.close()


class DbModel(Base, SessionWrapper, Lockable):
    """Abstract database model class.

    Subclasses should
    """
    __abstract__ = True

    @property
    def _models(self) -> List['DbModel']:
        """Used in `DbModel.session()` to add nested `DbModel` instances
        """
        return [attr for attr in self.__dict__.values()
                if isinstance(attr, DbModel)] + [self]

    def get(self, attr: str) -> Any:
        """Get attribute value from database
        """
        with self.session():
            return getattr(self, attr)

    @contextmanager
    def session(self, add: bool = True):
        """``SQLAlchemy`` session context manager.

        Opens a ``SQLAlchemy`` session and commits after the block is done.
        Changes are rolled back if an exception is raised. Usage::

            with self.session() as s:
                # interact with the database here

        Calls ``DbModel._pre()`` before yielding the session and
        ``DbModel._post()`` after the block is completed.

        Parameters
        ----------
        add: bool
            add model(s) after opening the session
        """
        with self.lock():
            log.vdebug(f'opening session')
            session = self._session_factory()

            try:
                if add:
                    for model in self._models:
                        self._retry_add(session, model)
                else:
                    self._retry_add(session, self)

                self._pre()
                yield session
                self._post()
                log.vdebug('committing')
                session.commit()
            except Exception as e:
                log.error(f"error during session: {e.args}")
                log.error('rolling back')
                session.rollback()
                raise
            finally:
                log.vdebug(f'closing session')
                session.close()

    @staticmethod
    def _retry_add(session, model: 'DbModel', retry: bool = False):
        try:
            session.add(model)
        except InvalidRequestError:
            if not retry:
                time.sleep(0.1)
                DbModel._retry_add(session, model, retry=True)
            else:
                raise

    def _pre(self):
        if hasattr(self, 'added') and self.added is None:
            self.added = datetime.datetime.now()
        if hasattr(self, 'modified'):
            self.modified = datetime.datetime.now()

    def _post(self):
        pass


class FileModel(DbModel):
    """Abstract database model for files.

    Files are hashed and resolved in order to keep a single entry per file.
    """
    __abstract__ = True
    _hash_q: queue.Queue
    _resolved: bool
    _path: str

    id = Column(Integer, primary_key=True)

    hash = Column(String, unique=True)
    path = Column(String)

    used = Column(DateTime)

    def __init__(self, path: str):
        self._resolved = False
        if path is not None:
            self._queue_hash(path)

    @property
    def resolved(self) -> bool:
        """Whether the ``FileModel`` has been resolved"""
        if hasattr(self, '_resolved'):
            return self._resolved
        else:
            return False

    def _queue_hash(self, path: str) -> None:
        self._path = path
        if self._check_file():
            self._hash_q = hash_file(self._path)
        else:
            raise ValueError
        if not self._hash_q.qsize():
            log.debug(f"queueing hash for {path}")

    def _get_hash(self) -> str:
        try:
            return self._hash_q.get()
        except AttributeError:
            raise RootException(f"{self.__class__.__qualname__}: "
                                f"get_hash() was called before queue_hash()")

    def _check_file(self):
        if self._path is not None:
            return os.path.isfile(self._path)
        else:
            return False

    def _join(self):
        if self.hash is None:
            if self._hash_q is not None:
                while not self._hash_q.qsize():
                    time.sleep(0.01)

    def resolve(self) -> 'FileModel':
        """Resolve the file by its SHA1 hash ~ :func:`~shapeflow.util.hash_file`.

        If the computed hash is new, the file is committed to the database.
        Otherwise, the original entry is re-used.

        Returns
        -------
        FileModel
            The current instance if the file is new, or a new ``FileModel``
            instance representing the original database entry.
        """
        if not self.resolved:
            self._join()
            hash = self._get_hash()

            with self.session(add=False) as s:
                match = s.query(self.__class__).filter_by(hash=hash).first()

                if match is None:
                    s.add(self)
                    self.hash = hash
                    self.path = self._path
                    file = self
                else:
                    file = match
                    file.connect(self)

                    # If current path is different, update history
                    if self._path != file.path:
                        file.path = self._path

                    if object_state(self).persistent:
                        s.delete(self)
                file._resolved = True
                file.used = datetime.datetime.now()
            return file
        else:
            return self


class BaseAnalysisModel(DbModel):
    """AnalysisModel interface.
    """
    __abstract__ = True

    @abc.abstractmethod
    def get_name(self) -> str:
        """Get the name of the analysis"""

    @abc.abstractmethod
    def get_config_json(self) -> Optional[str]:
        """Get the current configuration in JSON"""

    @abc.abstractmethod
    def load_config(self, video_path: str, design_path: str = None, include: List[str] = None) -> Optional[dict]:
        """Load configuration from the database"""

    @abc.abstractmethod
    def get_undo_config(self, context: str = None) -> Tuple[Optional[dict], Optional[int]]:
        """Undo configuration. If a ``context`` is supplied, ensure that the
        ``context`` field changes, but the other fields remain the same"""

    @abc.abstractmethod
    def get_redo_config(self, context: str = None) -> Tuple[Optional[dict], Optional[int]]:
        """Redo configuration. If a ``context`` is supplied, ensure that the
        ``context`` field changes, but the other fields remain the same"""

    @abc.abstractmethod
    def store(self) -> None:
        """Store analysis information from wrapped ``BaseVideoAnalyzer``
        to the database"""

    @abc.abstractmethod
    def export_result(self, run: int = None) -> None:
        """Export a result from the database"""

    @abc.abstractmethod
    def get_runs(self) -> int:
        """Get th number of runs of this analysis"""

    @abc.abstractmethod
    def get_id(self) -> int:
        """Get the id of this analysis"""
