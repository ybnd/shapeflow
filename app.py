"""
Execute .app.py ~ .venv environment
"""

import os
import subprocess

environment = '.venv'

if os.path.isdir(environment):
    if os.path.isdir(os.path.join(environment, 'bin')):
        executable = os.path.join(environment, 'bin/python')
    elif os.path.isdir(os.path.join(environment, 'Scripts')):
        executable = os.path.join(environment, 'Scripts/python')
    else:
        raise OSError('The virtual environment has an unexpected format.')

    subprocess.check_call([executable, '.app.py'])
else:
    raise EnvironmentError(f"No virtual environment in {environment}.")

