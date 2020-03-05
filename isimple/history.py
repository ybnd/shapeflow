import os
import time
import json

from isimple.core import ROOTDIR, settings
from isimple.core import get_logger
from isimple.core.config import Config
from isimple.core.common import RootException, RootInstance
from isimple.core.backend import Analyzer

from isimple.dbcore import Model, Database, types



log = get_logger(__name__)


class AnalysisModel(Model):
    _table = 'analyses'
    _flex_table = 'analysis_attributes'
    _fields: dict = {
        'id': types.PRIMARY_ID,

        'hash_video': types.INTEGER,        # todo: represents the video file(s) used in the analysis fully, without linking to path
        'hash_design': types.INTEGER,       # todo: represents the design file(s) used in the analysis fully, without linking to path
        'analyzer_type': types.STRING,      # type of the analyzer (resolved ~ isimple.core.config.AnalyzerConfig)
        'config': types.STRING,             # configuration (JSON)

        'description': types.STRING,        # description of the analysis
        'added': types.DATE,                # date&time when this analysis was added
        'done': types.BOOLEAN,
        'start_date': types.DATE,           # date&time when this analysis was added
        'finish_date': types.DATE,          # date&time when this analysis was added
        'elapsed': types.FLOAT,             # duration of analysis (in seconds)
    }

    _search_fields = (
        'hash_video', 'hash_design', 'description', 'analyzer_type', 'added',
    )

    @classmethod
    def _getters(cls):
        return {}

class History(Database):
    path = os.path.join(ROOTDIR, 'history.db')

    _models = (AnalysisModel,)

    def __init__(self, timeout=1.0):
        super().__init__(self.path, timeout)

    def new_analysis(self, analyzer: Analyzer) -> AnalysisModel:
        if isinstance(analyzer._config.video_path, list):
            settings.format.db_list_separator.join(analyzer._config.video_path)
        if isinstance(analyzer._config.design_path, list):
            settings.format.db_list_separator.join(analyzer._config.design_path)

        return AnalysisModel(
            db=self,
            id=hash(analyzer),
            description=analyzer.description,
            hash_video=analyzer.hash_video(),  # todo: hash the *files*, not the filenames!
            hash_design=analyzer.hash_design(),
            analyzer_type=analyzer.__class__.__str__,
            added=time.time(),
            config=json.dumps(analyzer._config.to_dict(do_tag=True)),
        )


def __clear_history__():
    os.remove(os.path.join(ROOTDIR, 'history.db'))