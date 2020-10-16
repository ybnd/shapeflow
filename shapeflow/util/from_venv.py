"""
Execute a Python script from virtual environment
"""

import sys
import os
import subprocess

environment = '.venv'

if __name__ == '__main__':
    script = sys.argv[1]        # the script to execute
    arguments = sys.argv[2:]    # and pass the rest of the arguments on to.

    if os.path.isdir(environment):
        unix_dir = os.path.join(environment, 'bin')
        win_dir = os.path.join(environment, 'Scripts')
        
        if os.path.isdir(unix_dir):
            pre = []
            executable = os.path.join(unix_dir, 'python')
            shell = False
        elif os.path.isdir(win_dir):
            pre = ["set", f"PATH='%PATH%{os.path.abspath(win_dir)};\\'", "&&"]
            executable = os.path.join(win_dir, 'python')
            shell = True
        else:
            raise OSError('The virtual environment has an unexpected format.')

        try:
            subprocess.check_call(pre + [executable, script] + arguments, shell=shell)
        except KeyboardInterrupt:
            # don't print exception on Ctrl+C
            pass
        except Exception:
            # re-raise any other exceptions
            raise

    else:
        raise EnvironmentError(f"No virtual environment in {environment}.")
