import threading
from frame_buffer import FrameBuffer
import tkinter as tk
from typing import Tuple
import time
import cv2
import numpy as np
from PIL import Image, ImageTk

class FrameLoop(threading.Thread):
    def __init__(self, capture, buffer: FrameBuffer, tk_label: tk.Label, minimum_frame_delta: float, max_image_size: Tuple[int, int], *args, **kwargs):
        self.cap = capture
        self.max_image_width = max_image_size[0]
        self.max_image_height = max_image_size[1]
        ret, frame = self.cap.read()
        if ret:
            h, w = frame.shape[:2]
            self.aspect = w / h
            # interpolation method
            if h > self.max_image_height or w > self.max_image_width:  # shrinking image
                self.interp = cv2.INTER_AREA
            else:  # stretching image
                self.interp = cv2.INTER_CUBIC
        else:
            self.aspect = 4 / 3  # default to 4/3 ratio
            self.interp = cv2.INTER_LINEAR  # default to linear scaling?
        self.buffer = buffer
        self.label = tk_label
        self.minimum_frame_delta = minimum_frame_delta
        self.cancel = threading.Event()
        self.paused = False
        super().__init__(*args, **kwargs)

    def run(self) -> None:
        while not self.cancel.is_set():
            while self.paused:
                pass
            frame_start = time.time()

            # Capture the video frame
            # by frame
            ret, frame = self.cap.read()

            if not ret and not self.paused:
                print("Can't receive frame (stream end?). Exiting ...")
                break

            if self.paused:
                continue

            # scale frame to fit
            if self.aspect > 1:
                scaled_width = self.max_image_width
                scaled_height = np.round(scaled_width/self.aspect).astype(int)
            elif self.aspect < 1:
                scaled_height = self.max_image_height
                scaled_width = np.round(scaled_height * self.aspect).astype(int)
            else:
                scaled_height = self.max_image_height
                scaled_width = scaled_height
            image = cv2.resize(frame, (scaled_width, scaled_height), self.interp)

            # Display the resulting frame
            image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            image = Image.fromarray(image)
            imagetk = ImageTk.PhotoImage(image)
            self.label.configure(image=imagetk)
            self.label.image = imagetk

            # buffer this frame
            self.buffer.write(cv2.imencode('.jpg', frame)[1].tobytes())

            # print(time.time()-frame_start)
            while (time.time() - frame_start) < self.minimum_frame_delta:
                pass

    def update_cap(self, new_cap_index):
        self.paused = True
        self.cap = cv2.VideoCapture(new_cap_index)
        ret, frame = self.cap.read()
        if ret:
            h, w = frame.shape[:2]
            self.aspect = w / h
            # interpolation method
            if h > self.max_image_height or w > self.max_image_width:  # shrinking image
                self.interp = cv2.INTER_AREA
            else:  # stretching image
                self.interp = cv2.INTER_CUBIC
        else:
            self.aspect = 4 / 3  # default to 4/3 ratio
            self.interp = cv2.INTER_LINEAR  # default to linear scaling?
        self.paused = False