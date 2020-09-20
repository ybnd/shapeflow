import argparse
import tkinter as tk
import tkinter.filedialog

parser = argparse.ArgumentParser()

parser.add_argument('--save', dest='save', action='store_true')
parser.add_argument('--load', dest='load', action='store_true')
parser.add_argument('--title', type=str, default='Select a file')
parser.add_argument('--filedesc', type=str, default=None)
parser.add_argument('--filetypes', type=str, default=None)
parser.set_defaults(save=None, load=None)

root = tk.Tk()
root.withdraw()

if __name__ == '__main__':
    args = parser.parse_args()

    if args.save is None and args.load is None:
        raise ValueError("Either '--save' or '--load' must be provided!")

    if args.filetypes is not None:
        if args.filedesc is None:
            args.filedesc = args.filetypes
        filetypes = [(args.filedesc, args.filetypes)]

        if args.save:
            path = tkinter.filedialog.asksaveasfilename(
                title=args.title, filetypes=filetypes
            )
        elif args.load:
            path = tkinter.filedialog.askopenfilename(
                title=args.title, filetypes=filetypes
            )
    else:
        if args.save:
            path = tkinter.filedialog.asksaveasfilename(
                title=args.title
            )
        elif args.load:
            path = tkinter.filedialog.askopenfilename(
                title=args.title
            )

    print(path)  # can be read with `out, err = p.communicate()`
