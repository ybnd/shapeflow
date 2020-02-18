import yaml
from yaml.representer import SafeRepresenter
import json
import os
import time
import pandas as pd
import warnings
from typing import List, Optional


class EnforcedStr(object):
    _options: List[str] = ['']
    _str: str

    def __init__(self, string: str = None):
        if string is not None:
            if string not in self.options:
                warnings.warn(f"Illegal {self.__class__.__name__} '{string}', "
                              f"should be one of {self.options}. "
                              f"Defaulting to '{self.default}'.")
                self._str = self.default
            else:
                self._str = string
        else:
            self._str = self.default

    def __repr__(self):
        return f"<{self.__class__.__name__} '{self._str}'>"

    def __str__(self):
        return self._str

    def __eq__(self, other):
        if hasattr(other, '_str'):
            return self._str == other._str
        elif isinstance(other, str):
            return self._str == other
        else:
            return False

    @property
    def options(self):
        return self._options

    @property
    def default(self):
        return self._options[0]


class Factory(EnforcedStr):
    _mapping: dict = {}
    _default: Optional[str] = None

    def get(self) -> type:
        if self._str in self._mapping:
            return self._mapping[self._str]
        else:
            raise ValueError(f"Factory {self.__class__.__name__} doesn't map"
                             f"{self._str} to a class.")

    @classmethod
    def get_str(cls, mapped_value):
        str = cls.default
        for k,v in cls._mapping.items():
            if mapped_value == v:
                str = k

        return str

    @property
    def options(self):
        return list(self._mapping.keys())

    @property
    def default(self):
        if self._default is not None:
            return self._default
        else:
            return list(self._mapping.keys())[0]

    @classmethod
    def extend(cls, mapping: dict):
        # todo: sanity check this
        cls._mapping.update(mapping)

class ColorSpace(EnforcedStr):
    _options = ['hsv', 'bgr', 'rgb']


class FrameIntervalSetting(EnforcedStr):  # todo: this is a horrible name
    _options = ['dt', 'Nf']


# https://stackoverflow.com/questions/16782112
yaml.add_representer(
    dict, lambda self,
    data: yaml.representer.SafeRepresenter.represent_dict(self, data.items())
)

# Extension
__ext__ = '.meta'

# Fields
__video__ = 'video'
__design__ = 'design'
__height__ = 'height (mm)'
__timestep__ = 'timestep (s)'
__coordinates__ = 'coordinates'
__transform__ = 'transform'
__order__ = 'order'
__colors__ = 'colors'
__from__ = 'from'
__to__ = 'to'

# Excel sheet name
__meta_sheet__ = 'metadata'


# todo: metadata handling needs to be consolidated with configuration handling in isimple.video

def bundle(video_path, design_path, coordinates, transform, order, colors, height, dt) -> dict:
    return {
        __video__: video_path,
        __design__: design_path,
        __height__: height,
        __timestep__: dt,
        __coordinates__: coordinates,
        __transform__: transform,
        __order__: order,
        __colors__: colors
    }


def colors_from_masks(masks: list):
    # Check if passed objects have filter_from and filter_to implemented
    if all([hasattr(mask, 'filter_from') and hasattr(mask, 'filter_to') for mask in masks]):
        colors = {
            mask.name: {__from__: mask.filter_from.tolist(), __to__: mask.filter_to.tolist()}
            for mask in masks
        }

        return colors
    else:
        TypeError('Incorrect list of Mask objects provided')


def bundle_readable(video_path, design_path, coordinates, transform, order, colors, height, dt) -> dict:

    # Make coordinates 'readable' in YAML
    coordinates = json.dumps(coordinates)

    # Make transform 'readable' in YAML
    transform = json.dumps(transform)

    order = json.dumps(order)

    # Make colors 'readable' in YAML
    for mask in colors.keys():
        colors[mask] = json.dumps(colors[mask])

    return {
        __video__: video_path,
        __design__: design_path,
        __height__: height,
        __timestep__: dt,
        __coordinates__: coordinates,
        __transform__: transform,
        __order__: order,
        __colors__: colors
    }


def save(video_path, design_path, coordinates, transform, order, colors, height, dt):
    # Keep metadata history in .meta file

    path = os.path.splitext(video_path)[0] + __ext__

    if os.path.isfile(path):
        history = '\n\n #######################\n # ' + \
                  time.strftime(
                      '%Y/%m/%d %H:%M:%S', time.localtime(
                          os.path.getmtime(path)
                      )
                  ) + ' #\n #######################\n'
        with open(path, 'r') as f:
            for line in f:
                history += ' #' + line
    else:
        history = ''

    meta = bundle_readable(path, design_path, coordinates, transform, order, colors, height, dt)

    with open(path, 'w+') as f:
        f.write(
            yaml.dump(
                {
                    __video__: meta[__video__],
                    __design__: meta[__design__],
                    __height__: meta[__height__],
                    __timestep__: meta[__timestep__],
                    __coordinates__: meta[__coordinates__],
                    __transform__: meta[__transform__],
                    __order__: meta[__order__],
                    __colors__: meta[__colors__],
                }, width=100000
            )
        )
        f.write(history)


def save_to_excel(meta, writer, sheet=__meta_sheet__):
    __gap__ = 1
    __file_r__ = 2
    __series_r__ = 2
    __points_r__ = 5
    __points_c__ = 3

    files = [__video__, __design__]
    df_files = pd.DataFrame([meta[k] for k in files], index=files)

    series = [__height__, __timestep__]
    df_series = pd.DataFrame([meta[k] for k in series], index=series)

    coordinates = ['pt' + str(i) for i in range(4)]
    df_coordinates = pd.DataFrame(meta[__coordinates__], index=coordinates, columns=['x', 'y'])

    df_transform = pd.DataFrame(meta[__transform__])
    df_colors = pd.DataFrame(meta[__colors__]).transpose()

    df_files.to_excel(
        writer, sheet_name=sheet, header=False,
    )
    df_series.to_excel(
        writer, sheet_name=sheet, header=False,
        startrow=__file_r__+__gap__
    )
    df_coordinates.to_excel(
        writer, sheet_name=sheet, index=True,
        startrow=__file_r__+__series_r__+2*__gap__
    )
    df_transform.to_excel(
        writer, sheet_name=sheet,
        startrow=__file_r__+__series_r__+2*__gap__, startcol=__points_c__ + __gap__
    )
    df_colors.to_excel(
        writer, sheet_name=sheet,
        startrow=__file_r__+__series_r__+__points_r__+3*__gap__
    )

    writer.save()


def load(video_path):
    path = os.path.splitext(video_path)[0] + __ext__
    try:
        with open(path, 'r') as f:
            meta = yaml.safe_load(f.read())

        if __height__ not in meta.keys():
            meta[__height__] = None

        if __timestep__ not in meta.keys():
            meta[__timestep__] = None

        # Parse transform back to array
        meta[__transform__] = json.loads(meta[__transform__])

        # Parse transform back to array
        meta[__coordinates__] = json.loads(meta[__coordinates__])

        meta[__order__] = tuple(json.loads(meta[__order__]))

        # Parse colors back to dicts
        for mask in meta[__colors__]:
            meta[__colors__][mask] = json.loads(meta[__colors__][mask])

        return meta
    except FileNotFoundError:
        return None
