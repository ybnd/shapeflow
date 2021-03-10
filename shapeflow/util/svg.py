"""Adapted from https://github.com/ybnd/OnionSVG
"""

import os
import re

from lxml import etree
import cairosvg as csvg


def check_svg(path) -> None:
    name, ext = os.path.splitext(path)
    if ext != 'svg':
        if os.path.exists(name + '.svg'):
            path = name + '.svg'

    try:
        with open(path, 'r') as f:
            data = f.read()
            data = bytes(data, encoding='UTF-8')
    except TypeError:
        raise TypeError(f"Invalid file")

    try:
        etree.fromstring(data)
    except etree.XMLSyntaxError:
        raise TypeError(f"Invalid file")


def peel(path, dpi, dir) -> None:
    SvgPeeler(path, dir, dpi=dpi).peel(
        'all'
    )
    print("\n")


class SvgPeeler:
    def __init__(self, path: str, to: str, dpi: int = 200):
        self.path = path
        self.dpi = dpi
        self.to = to

        name, ext = os.path.splitext(path)
        if ext != 'svg':
            if os.path.exists(name + '.svg'):
                path = name + '.svg'

        try:
            with open(path, 'r') as f:
                data = f.read()
                data = bytes(data, encoding='UTF-8')
        except TypeError:
            raise TypeError(f"Invalid file")

        self.original = data
        ddata = data.decode(encoding='UTF-8')
        self.header = bytes(ddata.split('<svg')[0], encoding='UTF-8')

        self.root = etree.fromstring(data)

        self.layers = []
        self.get_layers()

    def peel(self, select, dpi = None, to = None):
        print(f"\n Peeling... ({dpi} dpi)\n")

        if to is None:
            self.to = self.path.split('.')[0] + "_layers"
        else:
            self.to = to

        if dpi is None:
            dpi = self.dpi

        if os.path.exists(self.to):
            for file in os.listdir(self.to):
                os.remove(os.path.join(self.to, file))
        else:
            os.mkdir(self.to)

        if select == 'all':
            for layer in self.layers:
                if not layer.constant:
                    for hidden in self.layers:
                        hidden.hide()

                    layer.show()
                    self.save(_subdir(self.to, layer.label + '.png'), dpi)
        else:
            pattern = re.compile(select)

            for layer in self.layers:
                if pattern.match(layer.label):
                    if not layer.constant:
                        for hidden in self.layers:
                            hidden.hide()
                        layer.show()

                        self.save(_subdir(self.to, layer.label + '.png'), dpi)

        print("\n Done.")

    def get_layers(self):
        for child in self.root.getchildren():
            if child.tag[
                -1] == 'g':  # child is a layer-level group # todo: find a nicer way to do this
                for attribute in child.attrib.keys():
                    try:
                        if attribute.split('}')[1] == 'label':
                            self.layers.append(
                                Layer(child, child.attrib[attribute]))
                    except IndexError:
                        pass

    def as_svg(self):
        return self.header + etree.tostring(self.root)

    def list(self):
        print('\t')
        for layer in self.layers:
            print(f"{layer.label}")

    def save(self, path, dpi):
        csvg.svg2png(self.as_svg(), write_to=path,
                     scale=self.dpi2scale(dpi), unsafe=True)

        print(f"{os.path.relpath(path, self.path)}")

    @staticmethod
    def dpi2scale(dpi):
        # todo: this is a bit hacky
        default_dpi = 96
        return dpi / default_dpi


class Layer:
    def __init__(self, root, label):
        self.root = root
        self.label = label

        if self.label[0] == "_":
            self.constant = True
        else:
            self.constant = False

    def __repr__(self):
        try:
            if self.root.attrib['style'] == 'display:none':
                return f"<{self.label}: Hidden>"
            else:
                return f"<{self.label}: Shown>"
        except KeyError:
            return f"<{self.label}: Shown>"

    def hide(self):
        if not self.constant:
            self.root.attrib['style'] = 'display:none'
        else:
            self.show(False)

    def show(self, log_to_console=True):
        self.root.attrib['style'] = 'display:inline'
        if log_to_console:
            print(f"{self.label}", end=" --> ")


def _subdir(folder, filename):
    return os.path.join(os.path.join(os.getcwd(), folder), filename)