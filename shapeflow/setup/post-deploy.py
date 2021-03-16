from sys import executable
from subprocess import check_call


def sf(*args):
    check_call([executable, "sf.py", *args])

print("\nRunning setup/post-deploy.py ...\n")

sf("setup-cairo", "--cleanup")
sf("get-compiled-ui", "--replace")
sf("declutter")

print("\n\nAll done.")