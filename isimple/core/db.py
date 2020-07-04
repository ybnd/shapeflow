import abc
import multiprocessing
import os
import time
from contextlib import contextmanager
from typing import Optional, List, Type, Any, Tuple
import datetime

from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import scoped_session
from sqlalchemy.sql.schema import Column
from sqlalchemy.sql.sqltypes import Integer, String, DateTime

from isimple import get_logger
from isimple.core import RootException
from isimple.util import hash_file

log = get_logger(__name__)
Base = declarative_base()


class SessionWrapper(object):
    _session_factory: scoped_session

    def connect(self, session_wrapper: 'SessionWrapper'):
        self._session_factory = session_wrapper._session_factory

    @contextmanager
    def session(self):
        session = self._session_factory()
        try:
            yield session
            session.commit()
        except:
            session.rollback()
        finally:
            session.close()



class DbModel(Base, SessionWrapper):  # todo: shadowing pydantic here :/
    __abstract__ = True

    def _models(self) -> List['DbModel']:
        return [attr for attr in self.__dict__.values()
                if isinstance(attr, DbModel)] + [self]

    def get(self, attr) -> Any:
        with self.session():
            return getattr(self, attr)

    @contextmanager
    def session(self, add=True):
        log.vdebug(f'opening session')
        session = self._session_factory()
        if add:
            for model in self._models():
                session.add(model)
        try:
            self._pre()
            yield session
            self._post()
            log.vdebug('committing')
            session.commit()
        except:
            log.warning('rolling back')
            session.rollback()
            raise
        finally:
            log.vdebug(f'closing session')
            session.close()

    def _pre(self):
        if hasattr(self, 'added') and self.added is None:
            self.added = datetime.datetime.now()

    def _post(self):
        if hasattr(self, 'modified'):
            self.modified = datetime.datetime.now()

    def store(self):
        raise NotImplementedError


class FileModel(DbModel):
    __abstract__ = True
    _hash_q: multiprocessing.Queue
    _resolved: bool
    _path: str

    id = Column(Integer, primary_key=True)

    hash = Column(String)
    path = Column(String)

    used = Column(DateTime)

    def __init__(self, path: str):
        self._resolved = False
        if path is not None:
            self._queue_hash(path)

    @property
    def resolved(self):
        return self._resolved

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

    def join(self):
        if self.hash is None:
            if self._hash_q is not None:
                while not self._hash_q.qsize():
                    time.sleep(0.01)

    def resolve(self) -> 'FileModel':
        if not self.resolved:
            self.join()
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
                file._resolved = True
                file.used = datetime.datetime.now()
            return file
        else:
            return self


class BaseAnalysisModel(DbModel):
    __abstract__ = True

    @abc.abstractmethod
    def get_name(self) -> str:
        raise NotImplementedError

    @abc.abstractmethod
    def get_config_json(self) -> Optional[str]:
        raise NotImplementedError

    @abc.abstractmethod
    def load_config(self, video_path: str, design_path: str = None, include: List[str] = None) -> Optional[dict]:
        raise NotImplementedError

    @abc.abstractmethod
    def undo_config(self, context: str = None) -> Optional[dict]:
        raise NotImplementedError

    @abc.abstractmethod
    def redo_config(self, context: str = None) -> Optional[dict]:
        raise NotImplementedError
