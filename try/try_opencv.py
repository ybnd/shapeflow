import cv2
import os
from PIL import Image, ImageTk

import tkinter as tk

window = tk.Tk()
window.title('This is window.')

ratio = 4


cap = cv2.VideoCapture(os.path.join(os.getcwd(), "video2.mp4"))

frameN = cap.get(cv2.CAP_PROP_FRAME_COUNT)

cap.set(cv2.CAP_PROP_POS_FRAMES, int(frameN/2))
ret, frame = cap.read()

height, width, channels = frame.shape
canvas = tk.Canvas(window, width = int(width/ratio), height = int(height/ratio))
canvas.pack()

img = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
img = Image.fromarray(img)
img.thumbnail((int(width/ratio),int(height/ratio)))
img = ImageTk.PhotoImage(image = img)
canvas.create_image(0, 0, image = img, anchor = tk.NW)

window.mainloop()