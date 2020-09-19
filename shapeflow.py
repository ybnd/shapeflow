import sys
import subprocess

try:
    subprocess.check_call(
        ['python', 'shapeflow/util/from_venv.py', '__main__.py', *sys.argv[1:]]
    )
except KeyboardInterrupt:
    pass
