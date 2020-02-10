import yaml
from yaml.representer import SafeRepresenter
import json
import os
import time
import pandas as pd

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
