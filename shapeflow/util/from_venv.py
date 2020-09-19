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
        unix_dir = os.path.join(environment, 'bin')
        win_dir = os.path.join(environment, 'Scripts')
        
        if os.path.isdir(unix_dir):
            pre = []
            executable = os.path.join(unix_dir, 'python')
            shell = False
        elif os.path.isdir(win_dir):
            pre = ["set", f"PATH='%PATH%{os.path.abspath(win_dir)};\\'", "&&", "echo", "%PATH%" , "&&"]
            print(pre)
            executable = os.path.join(win_dir, 'python')
            shell = True
        else:
            raise OSError('The virtual environment has an unexpected format.')
            
        print(executable)

        try:
            subprocess.Popen(pre + [executable, args.script] + unknownargs, shell=shell)
        except KeyboardInterrupt:
            pass
    else:
        raise EnvironmentError(f"No virtual environment in {environment}.")