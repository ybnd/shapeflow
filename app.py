import sys
import subprocess

try:
    subprocess.check_call(
        ['python', '.venv.py', '.server.py', '--open', *sys.argv[1:]]
    )
except KeyboardInterrupt:
    pass
