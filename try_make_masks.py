from lxml import etree
import cairosvg as csvg
import os
import shutil

shutil.rmtree('./overlay')

with open("shuttle_overlay.svg", 'r') as f:
    data = f.read()
    data = bytes(data, encoding='UTF-8')

root = etree.fromstring(data)
width = root.xpath('@width')[0]
height = root.xpath('@height')[0]

units = root.xpath('*/@units')[0]

def dpi2scale(dpi):
    default_dpi = 96
    return dpi / default_dpi

def tempdir(filename):
    folder = os.path.join(os.getcwd(), "temp")
    if not os.path.isdir(folder):
        os.mkdir(folder)
    return os.path.join(folder, filename)

def subdir(folder, filename):
    if not os.path.isdir(folder):
        os.mkdir(os.path.join(os.getcwd(), folder))
    return os.path.join(os.path.join(os.getcwd(), folder), filename)

# Full render
# csvg.svg2png(data, write_to = tempdir("cairo_overlay.png"), scale = dpi2scale(400))

class LayerSwitch:
    def __init__(self, data: bytes, dpi: int = None):
        self.original = data
        ddata = data.decode(encoding = 'UTF-8')
        self.header = bytes(ddata.split('<svg')[0], encoding = 'UTF-8')

        self.root = etree.fromstring(data)

        if dpi is None:
            self.dpi = 400
        else:
            self.dpi = dpi

        self.scale = dpi2scale(self.dpi)

        self.get_layers()

    def get_layers(self):
        self.layers = []
        self.slayers = []
        self.clayers = []
        for child in self.root.getchildren():
            if child.tag[-1] == 'g': # child is a layer-level group # todo: better way to do this?
                for attribute in child.attrib.keys():
                    try:
                        if attribute.split('}')[1] == 'label':
                            self.layers.append(Layer(child, child.attrib[attribute]))
                    except IndexError:
                        pass

        for layer in self.layers:
            if layer.label[0] == "_":
                self.clayers.append(layer)
            else:
                self.slayers.append(layer)

    def tostring(self):
        return self.header + etree.tostring(self.root)

    def save(self, path):
        csvg.svg2png(self.tostring(), write_to = path, scale = self.scale, unsafe = True)

    def save_all(self, folder):
        for constant in self.clayers:
            constant.show()

        for layer in self.slayers:
            for hidden in self.slayers:
                hidden.hide()

            layer.show()
            self.save(subdir(folder, layer.label + '.png'))

class Layer:
    def __init__(self, root, label):
        self.root = root
        self.label = label

    def __repr__(self):
        if self.root.attrib['style'] == 'display:none': return f"<Layer {self.label}: Hidden>"
        else: return f"<Layer {self.label}: Displayed>"

    def hide(self):
        self.root.attrib['style'] = 'display:none'

    def show(self):
        self.root.attrib['style'] = 'display:inline'

svg = LayerSwitch(data, dpi = 400)
svg.save_all('overlay')