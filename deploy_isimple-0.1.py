# Bootstrap a virtual environment (see https://github.com/ybnd/bootstrap-venv)
import os
from distutils.util import strtobool
import subprocess


url = "https://github.com/ybnd/isimple.git"
environment = ".venv"
branch = "0.1"
name = "isimple-0.1"

deploy_git = '''# Bootstrap .git connection with GitPython

import os
import glob
import shutil
from git import Repo

url = "https://github.com/ybnd/isimple.git"
branch = "0.1"

cwd = os.getcwd()

assert isinstance(url, str)

if os.path.isdir('.git'):
    print(f"Opening repository in {cwd}")
    repo = Repo(cwd)
else:
    print(f"Cloning remote repository from {url} to {cwd}")
    repo = Repo.clone_from(url, os.path.join(cwd, "isimple-0.1"))

repo.git.checkout(branch)

# Move clone into parent directory (cwd)
for i in glob.glob('isimple-0.1/*') + glob.glob('isimple-0.1/.*'):
    shutil.move(i, cwd)

# Remove the (empty) clone directory
shutil.rmtree('isimple-0.1')'''
setup = '''import os
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
            shutil.move(file, ".venv/Scripts/")
    else:
        # 32-bit Python
        for file in glob.glob('cairo*/lib/x86/cairo*'):
            shutil.move(file, ".venv/Scripts/")

    # Delete the rest of the cairo files
    os.remove('cairo.zip')
    shutil.rmtree(glob.glob('cairo*')[0])

    # Hide dotfiles
    os.mkdir('.render')
    os.mkdir('.cache')

    nondot = [
        'mypy.ini',
        'tox.ini',
        'codecov.yml',
        'requirements.txt',
        'docs',
        'test',
    ]

    for file in glob.glob('.*') + nondot:
        if os.path.exists(file):
            os.system('attrib +h ' + file)
'''

do = strtobool(
    input(f"Deploy {name} from {url} ({branch}) into {os.getcwd()}? (y/n) \n")
)

if do:
    # Create a virtual environment in .venv
    subprocess.check_call(['python', '-m', 'venv', environment])

    if os.path.isdir(os.path.join(environment, 'bin')):
        executable = os.path.join(environment, 'bin/python')
    elif os.path.isdir(os.path.join(environment, 'Scripts')):
        executable = os.path.join(environment, 'Scripts/python')
    else:
        raise OSError('The virtual environment has an unexpected format.')

    # Install requirements
    subprocess.check_call([executable, '-m', 'pip', 'install', '--upgrade', 'pip'])
    subprocess.check_call([executable, '-m', 'pip', 'install', *['GitPython']])

    # Set up .git
    subprocess.check_call([executable, '-c', deploy_git])

    # Install requirements
    subprocess.check_call([executable, '-m', 'pip', 'install', '-r', 'requirements.txt'])

    if setup:
        subprocess.check_call([executable, '-c', setup])

    # Write scripts to file
    update = "scripts/update.py"
    if not os.path.isdir(os.path.dirname(update)):
        os.mkdir(os.path.dirname(update))

    with open(update, 'w+') as f:
        f.write('''# Update repository ~ git pull
import os
import subprocess
from git import Repo


if __name__ == '__main__':
    repo = Repo(isimple-0.1)
    Repo.git.checkout(0.1)
    Repo.git.pull()
''')

    # Remove this script
    os.remove(__file__)

    input('\n\nDone. ')