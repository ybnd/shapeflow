from sys import executable
from subprocess import check_call, CalledProcessError


def sf(*args):
    try:
        check_call([executable, "sf.py", *args])
    except CalledProcessError as e:
        print(e.cmd)


if __name__ == '__main__':
    print("\nRunning setup/post-deploy.py ...\n")

    sf("setup-cairo", "--cleanup")
    sf("get-compiled-ui", "--replace")
    sf("declutter")

    print("\n\nDone.")
