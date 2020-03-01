# cheated off of https://testdriven.io/blog/developing-a-single-page-app-with-flask-and-vuejs/

from typing import List

from flask import Flask, jsonify, request
from flask_cors import CORS

from isimple.core.common import Manager
from isimple.video import backend, VideoAnalyzer


# run a backend instance
b = VideoAnalyzer()

# configuration
DEBUG = True

# instantiate the app
app = Flask(__name__)
app.config.from_object(__name__)

# enable CORS
CORS(app, resources={r'/*': {'origins': '*'}})

def respond(data: dict = None, errors: List[dict] = None) -> str:
    if errors is None:
        return jsonify({'data': data})
    else:
        return jsonify({'errors': errors})


@app.route('/get_config', methods=['GET'])
def get_config():
    return respond(
        b.get(backend.get_config)()  # todo: doing a Manager 'get' every time is overkill, especially when e.g. requesting frames
    )

@app.route('/set_config', methods=['POST'])
def set_config():
    try:
        b.get(backend.set_config)(request.get_json().get('config'))
        return respond()
    except Exception:
        pass

if __name__ == '__main__':
    app.run()
