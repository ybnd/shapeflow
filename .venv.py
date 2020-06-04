"""
Execute a Python script from virtual environment
"""

import os
import subprocess

import argparse

environment = '.venv'

parser = argparse.ArgumentParser(
    description='Execute script ~ .venv virtual environment'
)
parser.add_argument('script', type=str, help="Path to script")

if __name__ == '__main__':
    args, unknownargs = parser.parse_known_args()

    if os.path.isdir(environment):
        if os.path.isdir(os.path.join(environment, 'bin')):
            executable = os.path.join(environment, 'bin/python')
        elif os.path.isdir(os.path.join(environment, 'Scripts')):
            executable = os.path.join(environment, 'Scripts/python')
        else:
            raise OSError('The virtual environment has an unexpected format.')

        try:
            subprocess.Popen([executable, args.script] + unknownargs)
        except KeyboardInterrupt:
            pass
    else:
        raise EnvironmentError(f"No virtual environment in {environment}.")