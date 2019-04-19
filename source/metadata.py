import yaml
import json
import os

# https://stackoverflow.com/questions/16782112/can-pyyaml-dump-dict-items-in-non-alphabetical-order
yaml.add_representer(dict, lambda self, data: yaml.representer.SafeRepresenter.represent_dict(self, data.items()))


def save(video_path, design_path, transform, colors):
    path = os.path.splitext(video_path)[0] + '.meta'

    # Make transform 'readable' in YAML
    transform = json.dumps(transform)

    # Make colors 'readable' in YAML
    for mask in colors.keys():
        colors[mask] = json.dumps(colors[mask])

    with open(path, 'w+') as f:
        f.write(
            yaml.dump(
                {
                    'video': video_path,
                    'design': design_path,
                    'transform': transform,
                    'colors': colors,
                }
            )
        )


def load(video_path):
    path = os.path.splitext(video_path)[0] + '.meta'

    with open(path, 'r') as f:
        meta = yaml.load(f.read())

    # Parse transform back to array
    meta['transform'] = json.loads(meta['transform'])

    # Parse colors back to dicts
    for mask in meta['colors']:
        meta['colors'][mask] = json.loads(meta['colors'])



try_dict = {
    'video': 'this-video.mp4',
    'design': 'this-design.svg',
    'transform': '[[0,0,0],[0,0,0],[0,0,0]]',
    'colors': {
        'mask1': 'blablabla',
        'mask2': 'blablabla'
    }
}

with open('try-meta', 'w') as f:
    f.write(yaml.dump(try_dict))