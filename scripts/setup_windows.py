import os
import sys
import shutil
import glob
from urllib.request import urlretrieve
from zipfile import ZipFile


if os.name == 'nt':  # If running on Windows
    url = "https://github.com/preshing/cairo-windows/releases/download/1.15.12/cairo-windows-1.15.12.zip"
    urlretrieve(url, 'cairo.zip')
    
    with ZipFile('cairo.zip', 'r') as z:
        z.extractall()

    # Move cairo files to the /Scripts/ folder in the virtual environment
    if sys.maxsize > 2**32:
        # 64-bit Python
        for file in glob.glob('cairo*/lib/x64/cairo*'):
            shutil.move(file, "$environment/Scripts/")
    else:
        # 32-bit Python
        for file in glob.glob('cairo*/lib/x86/cairo*'):
            shutil.move(file, "$environment/Scripts/")

    # Delete the rest of the cairo files
    os.remove('cairo.zip')
    shutil.rmtree(glob.glob('cairo*')[0])

    # Hide dotfiles
    os.mkdir('.render')
    os.mkdir('.cache')

    nondot = ['mypy.ini', 'tox.ini', 'requirements.txt', 'docs']

    for file in glob.glob('.*') + nondot:
        if os.path.exists(file):
            os.system('attrib +h ' + file)
