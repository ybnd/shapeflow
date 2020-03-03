from flask import Flask, request
from flask_cors import CORS

from isimple.core.log import get_logger


log = get_logger(__name__)


DEBUG = True

app = Flask(__name__)
app.config.from_object(__name__)

CORS(app, resources={r'/*': {'origins': '*'}})  # todo: temporary!


if __name__ == '__main__':
    # todo: take CLI arguments for address, debug on/off, ...
    app.run()