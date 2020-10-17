# shapeflow

### Setting up a development environment

To work on shapeflow, you should set up a vritual environment in `.venv`

```
python -m venv .venv
(.venv) pip install -r requirements.txt
```

With this environment in place, the entrypoint `shapeflow.py` can be run either from `(.venv)` or with your the global Python interpreter. In the latter case, `.venv` will be used implicitly.

To work on the frontend, set up `ui/` as elaborated [here](../ui/README.md).

### Adding plugins

[Features](../docs/features.md), [filters](../docs/filters.md) and [transforms](../docs/transforms.md) are handled by a plugin system. You can use [the existing plugins](plugins/) as examples.

* A plugin should be a subclass of its respective interface (`Feature` for features, `TransformInterface` for transforms and `FilterInterface` for filters)
* If you define configuration for the plugin, it should derive from its respective configuration class as well (`FeatureConfig` for features, `TransformConfig` for transforms and `FilterConfig` for filters), and should be linked to the plugin class itself as the class variable `_class_config`. Configuration parameters should be defined as `pydantic` `Field` instances, and should include a default and a description.
* Plugins should have short descriptive docstring
* Feature plugins should also define a `_label` and `_unit` as class variables. These values will be used to label the y-axis on the result page of the front-end.

All plugin files are automatically loaded by [`plugins/__init__.py`](plugins/__init__.py) when `shapeflow.plugins` is imported. 

