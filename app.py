import subprocess

try:
    subprocess.check_call(['python', '.venv.py', '.server.py', '--open'])
except KeyboardInterrupt:
    pass
