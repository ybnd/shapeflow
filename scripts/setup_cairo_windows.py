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
    for file in glob.glob('cairo*/lib/x64/cairo*'):
        shutil.move(file, "$environment/Scripts/")

    try:
        import cairocffi
    except OSError:
        for file in glob.glob('$environment/Scripts/cairo*'):
            os.remove(file)

        for file in glob.glob('cairo*/lib/x86/cairo*'):
            shutil.move(file, "$environment/Scripts/")

        try:
            import cairocffi
        except OSError:
            raise OSError('Could not load cairo from the virtual environment.')

    # Delete the rest of the cairo files
    os.remove('cairo.zip')
    shutil.rmtree(glob.glob('cairo*')[0])
