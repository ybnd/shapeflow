import os
from isimple.main import Main

os.chdir('..')

if __name__ == '__main__':
    main = Main()
    main.serve(True)
    main.cleanup()