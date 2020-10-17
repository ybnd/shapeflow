"""
Execute a Python script from virtual environment
"""

import sys
import os
import subprocess

environment = '.venv'


def from_venv():
    script = sys.argv[1]        # the script to execute
    arguments = sys.argv[2:]    # and pass the rest of the arguments on to.

    if os.path.isdir(environment):
        python = os.path.basename(sys.executable)

        formats = {
        # platform -> directory where the executable should be
            'unix': os.path.join(environment, 'bin'),
            'windows': os.path.join(environment, 'Scripts')
        }
        executable, platform, d = _get_executable(formats, python)

        if platform == 'unix':
            pre = []
            shell = False
        elif platform == 'windows':
            pre = ["set", f"PATH='%PATH%{os.path.abspath(d)};\\'", "&&"]
            shell = True
        else:
            raise EnvironmentError(
                'The virtual environment has an unexpected format.'
            )

        try:
            subprocess.check_call(
                pre + [executable, script] + arguments,
                shell=shell
            )
        except KeyboardInterrupt:
            # don't print exception on Ctrl+C
            pass
        except subprocess.CalledProcessError as e:
            exit(e.returncode)
        except Exception:
            # re-raise any other exceptions
            raise

    else:
        raise EnvironmentError(f"No virtual environment in {environment}.")


def _get_executable(formats, preferred_python):
    for platform, d in formats.items():
        if os.path.isdir(d) and len(os.listdir(d)) > 0:
            preferred = os.path.join(d, preferred_python)
            fallback = os.path.join(d, 'python')

            if os.path.isfile(preferred):
                return preferred, platform, d
            elif os.path.isfile(fallback):
                return fallback, platform, d
    return 'python', ''


if __name__ == '__main__':
    from_venv()
