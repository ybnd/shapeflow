from tkinter import Tk
import tkinter.filedialog
import argparse


Tk().withdraw()

parser = argparse.ArgumentParser()
parser.add_argument("--save", action="store_true")
parser.add_argument("--load", action="store_true")
parser.add_argument("--title", required=False)
parser.add_argument("--pattern", required=False)
parser.add_argument("--pattern_description", required=False)

if __name__ == '__main__':
    args = parser.parse_args()
    d = {
        "title": args.title,
        "filetypes": [(args.pattern_description, args.pattern)]
    }

    path = None

    if args.load or (not args.load and not args.save):
        path = tkinter.filedialog.askopenfilename(**d)
    elif args.save:
        path = tkinter.filedialog.asksaveasfilename(**d)

    if isinstance(path, str):
        print(path)  # can be read with `out, err = p.communicate()`
