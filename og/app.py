import json
from isimple import __history_path__


class HistoryApp(object):
    """Applications with history stored in JSON format in isimple/.history
    """
    def __init__(self, file):
        self.full_history = {}  # todo: should interact with isimple.video.VideoAnalysisElement._config
        self.history = {}

        self.key = file or __file__
        self.load_history()

    def reset_history(self):
        pass

    def load_history(self):
        try:
            with open(__history_path__, 'r') as f:
                self.full_history = json.load(f)

        except (
                json.decoder.JSONDecodeError, FileNotFoundError, KeyError
        ) as e:
            self.reset_history()
            if e is KeyError:
                self.full_history[self.key] = self.history
            else:
                self.full_history = {self.key: self.history}
        self.get_own_history()
        self.unpack_history()

    def save_history(self):
        self.pack_history()
        with open(__history_path__, 'w+') as f:
            json.dump(self.full_history, f, indent=2)

    def get_own_history(self):
        try:
            self.history = self.full_history[self.key]
        except KeyError:
            self.reset_history()
            self.full_history[self.key] = self.history

    def unpack_history(self):
        pass

    def pack_history(self):
        pass