# cheated off of https://testdriven.io/blog/developing-a-single-page-app-with-flask-and-vuejs/

import json

from flask import Flask, jsonify, request
from flask_cors import CORS

from isimple.core.log import get_logger
from isimple.core.schema import schema
from isimple.video import backend, BackendType


log = get_logger(__name__)

__instances__: dict = {
    BackendType('VideoAnalyzer'): [],
}

# configuration
DEBUG = True

# instantiate the app
app = Flask(__name__)
app.config.from_object(__name__)

# enable CORS
CORS(app, resources={r'/*': {'origins': '*'}})  # todo: temporary!


def respond(*args) -> str:  # todo: use method schemas
    return jsonify({'data': [*args]})


@app.route('/<backendtype>/init', methods=['GET'])
def init(backendtype: str):
    bt = BackendType(backendtype)
    __instances__[bt].append(bt.get()())  # todo: wow.
    return respond(len(__instances__[bt])-1)  # todo: should return list of methods that don't rely on nested BackendInstances & their schemas


@app.route('/<backendtype>/<index>/launch', methods=['GET'])
def launch(backendtype: str, index: int):
    bt = BackendType(backendtype)
    index = int(index)
    __instances__[bt][index].launch()  # todo: should also cache all method pointers for __instances__[bt][index] so we don't call .get() a million times
    return respond()  # todo: should return all available methods & their schemas


@app.route('/<backendtype>/<index>/schemas', methods=['GET'])
def get_schemas(backendtype: str, index: int):
    bt = BackendType(backendtype)
    index = int(index)
    i = __instances__[bt][index]
    return respond(
        {
            'config': schema(i._config.__class__),
            'methods': {e._name:schema(m[0]) for e, m in i._instance_mapping.items()},
        }
    )


@app.route('/<backendtype>/<index>/<method>', methods=['GET'])
def call(backendtype: str, index: int, method: str):
    bt = BackendType(backendtype)
    index = int(index)

    log.info(f"we have a request: {request.args.to_dict()}")

    if request.args.to_dict() != {}:
        return respond(  # todo: dict ~ method return schema
            __instances__[bt][index].get(  # todo: cache method pointers @ launch
                getattr(backend, method)
            )(**{k:json.loads(v) for k,v in request.args.to_dict().items()})  # todo: figure out how to route request data correctly ~ attr schema of method
        )
    else:
        return respond(  # todo: dict ~ method return schema
            __instances__[bt][index].get(  # todo: cache method pointers @ launch
                getattr(backend, method)
            )()  # todo: figure out how to route request data correctly ~ attr schema of method
        )


if __name__ == '__main__':
    # todo: take CLI arguments for address, debug on/off, ...
    # todo: server-level configuration
    app.run()

