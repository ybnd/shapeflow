from sys import executable
from subprocess import check_call, CalledProcessError


def sf(*args):
    check_call([executable, "sf.py", *args])


try:
    print("\nRunning setup/post-deploy.py ...\n")

    sf("setup-cairo", "--cleanup")
    sf("get-compiled-ui", "--replace")
    sf("declutter")

    print("\n\nDone.")
except CalledProcessError as e:
    print(f"Command failed: {e.cmd}")
    exit(1)
