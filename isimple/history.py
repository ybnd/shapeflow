import time
import datetime
import json

from isimple.core import settings
from isimple.core import get_logger
from isimple.core.backend import Analyzer

from isimple.dbcore import Model, Database, types


log = get_logger(__name__)


class ResultsModel(Model):
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

    @classmethod
    def _getters(cls):
        return {}


class AnalysisModel(Model):
    _analyzer: Analyzer

    _table = 'analyses'
    _flex_table = 'analysis_attributes'
    _fields: dict = {
        'id': types.PRIMARY_ID,

        'hash_video': types.STRING,
        'hash_design': types.STRING,

        'analyzer_type': types.STRING,      # type of the analyzer (resolved ~ isimple.core.config.AnalyzerConfig)
        'config': types.STRING,             # configuration (JSON)
        'results': types.FOREIGN_ID,        # ID of ResultsModel entry

        'description': types.STRING,        # description of the analysis
        'added': types.DATE,                # date&time when this analysis was added
        'start_date': types.DATE,           # date&time when this analysis was started
        'finish_date': types.DATE,          # date&time when this analysis was finished
        'elapsed': types.FLOAT,             # duration of analysis (in seconds)
    }

    _search_fields = (
        'hash_video', 'hash_design', 'description', 'analyzer_type', 'added',
    )

    def __init__(self, analizer: Analyzer):
        self._analyzer = analizer
        super().__init__()

    @classmethod
    def _getters(cls):
        return {}

    def store(self, fields = None):
        # Store analysis setup
        self.update({
            'hash_video': self._analyzer.hash_video,
            'hash_design': self._analyzer.hash_design,
            'analyzer_type': self._analyzer.__class__.__name__,
            'config': json.dumps(self._analyzer._config.to_dict()),
            'description': self._analyzer.description,
        })

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

        # Store timing info
        t = self._analyzer.timing
        if t is not None:
            fromt = datetime.datetime.fromtimestamp
            self.update({
                'start_date': t.t0,
                'finish_date': t.t1,
                'elapsed': t.elapsed,
            })

        super().store(fields)


class History(Database):
    path = settings.db.path

    _models = (AnalysisModel,ResultsModel,)
    _memotable: dict

    def __init__(self, timeout=1.0):
        super().__init__(self.path, timeout)

    def add_analysis(self, analyzer: Analyzer) -> AnalysisModel:
        model = AnalysisModel(analyzer)
        model.add(self)
        model.store()
        return model

    def add_results(self) -> ResultsModel:
        model = ResultsModel()
        model.add(self)
        model.store()
        return model
