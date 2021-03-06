from distutils.util import strtobool


# Declutter the repository
clutter = ['mypy.ini', 'tox.ini', '__pycache__']
# and files starting with '.*'

do = strtobool(
    input(f"Hide clutter files? (y/n) \n")
)

if do:
    import os

    if os.name == 'nt':
        # Windows

        import glob

        clutter += glob.glob('.*')

        # Pre-emptively create __pycache__ so we can hide it now.
        if not os.path.isdir('__pycache__'):
            os.mkdir('__pycache__')

        for file in clutter:
            os.system("attrib +h " + file)
    else:
        # something else
        with open('.hidden', 'w+') as f:
            f.write(
                "\n".join(clutter)
            )
