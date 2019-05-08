import yaml
import json
import os
import time

# https://stackoverflow.com/questions/16782112/can-pyyaml-dump-dict-items-in-non-alphabetical-order
yaml.add_representer(dict, lambda self, data: yaml.representer.SafeRepresenter.represent_dict(self, data.items()))


def bundle(video_path, design_path, coordinates, transform, order, colors) -> dict:


    # Make coordinates 'readable' in YAML
    coordinates = json.dumps(coordinates)

    # Make transform 'readable' in YAML
    transform = json.dumps(transform)

    order = json.dumps(order)

    # Make colors 'readable' in YAML
    for mask in colors.keys():
        colors[mask] = json.dumps(colors[mask])

    return {
        'video_path': video_path,
        'design_path': design_path,
        'coordinates': coordinates,
        'transform': transform,
        'order': order,
        'colors': colors
    }


def save(video_path, design_path, coordinates, transform, order, colors):
    # Keep metadata history in .meta file

    path = os.path.splitext(video_path)[0] + '.meta'

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

    meta = bundle(path, design_path, coordinates, transform, order, colors)

    with open(path, 'w+') as f:
        f.write(
            yaml.dump(
                {
                    'video': meta['video_path'],
                    'design': meta['design_path'],
                    'coordinates': meta['coordinates'],
                    'transform': meta['transform'],
                    'order': meta['order'],
                    'colors': meta['colors'],
                }, width=100000
            )
        )
        f.write(history)


def save_meta(meta: dict):
    path = os.path.splitext(meta['video_path'])[0] + '.meta'

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

    with open(path, 'w+') as f:
        f.write(
            yaml.dump(
                {
                    'video': meta['video_path'],
                    'design': meta['design_path'],
                    'coordinates': meta['coordinates'],
                    'transform': meta['transform'],
                    'order': meta['order'],
                    'colors': meta['colors'],
                }, width=100000
            )
        )
        f.write(history)



def load(video_path):
    path = os.path.splitext(video_path)[0] + '.meta'
    try:
        with open(path, 'r') as f:
            meta = yaml.safe_load(f.read())

        # Parse transform back to array
        meta['transform'] = json.loads(meta['transform'])

        # Parse transform back to array
        meta['coordinates'] = json.loads(meta['coordinates'])

        meta['order'] = tuple(json.loads(meta['order']))

        # Parse colors back to dicts
        for mask in meta['colors']:
            meta['colors'][mask] = json.loads(meta['colors'][mask])

        return meta
    except FileNotFoundError:
        return None