import json
import tkinter as tk
import time
from dataclasses import dataclass
from typing import Tuple

from PIL import Image, ImageTk
import threading
import cv2
import numpy as np
from frame_buffer import FrameBuffer
from stream_handler import StreamingHandler
from server_thread import ServerThread
from int_entry import IntEntry
import socket
from find_devices import FindDevices
import os
from usb.core import find
from usb.backend.libusb1 import get_backend
import usb.util


class FrameLoop(threading.Thread):
    def __init__(self, capture, buffer: FrameBuffer, tk_label: tk.Label, minimum_frame_delta: float, *args, **kwargs):
        self.cap = capture
        ret, frame = self.cap.read()
        if ret:
            h, w = frame.shape[:2]
            self.aspect = w / h
            # interpolation method
            if h > max_image_height or w > max_image_width:  # shrinking image
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
        super().__init__(*args, **kwargs)

    def run(self) -> None:
        while not self.cancel.is_set():
            frame_start = time.time()

            # Capture the video frame
            # by frame
            ret, frame = self.cap.read()

            if not ret:
                print("Can't receive frame (stream end?). Exiting ...")
                break

            # scale frame to fit
            if self.aspect > 1:
                scaled_width = max_image_width
                scaled_height = np.round(scaled_width/self.aspect).astype(int)
            elif self.aspect < 1:
                scaled_height = max_image_height
                scaled_width = np.round(scaled_height * self.aspect).astype(int)
            else:
                scaled_height = max_image_height
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

    def update_cap(self, new_cap):
        self.cap = new_cap
        ret, frame = self.cap.read()
        if ret:
            h, w = frame.shape[:2]
            self.aspect = w / h
            # interpolation method
            if h > max_image_height or w > max_image_width:  # shrinking image
                self.interp = cv2.INTER_AREA
            else:  # stretching image
                self.interp = cv2.INTER_CUBIC
        else:
            self.aspect = 4 / 3  # default to 4/3 ratio
            self.interp = cv2.INTER_LINEAR  # default to linear scaling?


def toggle_server():
    global active_socket
    if active_socket is None:
        server_address = ('', settings.server_port)
        active_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        active_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        active_socket.bind(server_address)
        active_socket.listen(5)
        active_server_threads.extend([
            ServerThread(
                server_address,
                lambda *args: StreamingHandler(frame_buffer, *args),
                active_socket
            ) for _ in range(25)
        ])
        serv_status.configure(image=active_status_img)
        serv_toggle.configure(text="Stop Server")
    else:
        for serv_thread in active_server_threads:
            serv_thread.shutdown()
        active_server_threads.clear()
        active_socket.close()
        active_socket = None
        serv_status.configure(image=inactive_status_img)
        serv_toggle.configure(text="Start Server")


@dataclass
class Settings:
    server_port: int
    minimum_frame_delta: float
    updated: bool = False


def save_settings(sett: Settings):
    with open('./empkam_settings.json', 'w') as file:
        json.dump({
            'server_port': sett.server_port,
            'minimum_frame_delta': sett.minimum_frame_delta
        }, file)


def open_settings_screen(sett: Settings):
    settings_screen = tk.Toplevel()
    settings_screen.title('Settings')
    # settings_screen.geometry('200x110')
    settings_screen.grid_columnconfigure(0, weight=1, uniform='sett')
    settings_screen.grid_columnconfigure(1, weight=1, uniform='sett')
    settings_screen.grid_rowconfigure(0, weight=1)
    settings_screen.grid_rowconfigure(1, weight=1)
    settings_screen.grid_rowconfigure(2, weight=1)
    settings_screen.resizable(False, False)

    def validate_fields():
        valid = True
        if port_field and len(port_field.get()) == 0:
            # TODO highlight error
            valid = False
        if frame_rate_field and len(frame_rate_field.get()) == 0:
            # TODO highlight error
            valid = False

        if not valid:
            save_btn.configure(state="disabled")
        else:
            save_btn.configure(state="normal")

    # port label
    tk.Label(settings_screen, text='Port:', anchor='e', width=12).grid(row=0, column=0, pady=5, padx=(5, 0))

    port_field = IntEntry(settings_screen, width=10, on_edit=validate_fields, initial_value=settings.server_port)
    port_field.grid(row=0, column=1, padx=5, pady=5, sticky='NESW')

    frame_rate = int(float(1/sett.minimum_frame_delta))

    # frame rate label
    tk.Label(settings_screen, text='Max Frame Rate:', anchor='e', width=12).grid(row=1, column=0, pady=5, padx=(5, 0))

    frame_rate_field = IntEntry(settings_screen, width=10)
    frame_rate_field.insert(0, str(frame_rate))
    frame_rate_field.grid(row=1, column=1, padx=5, pady=5, sticky='NESW')

    # TODO active webcam selector

    # save and cancel buttons
    tk.Button(
        settings_screen,
        text='Cancel',
        command=lambda: settings_screen.destroy(),
        width=7
    ).grid(row=3, column=0, padx=5, pady=7, sticky='E')

    def save():
        new_port = int(port_field.get())
        if new_port != sett.server_port:
            sett.server_port = new_port
            sett.updated = True
            if active_socket is not None:
                toggle_server()
                while len(active_server_threads) > 0:
                    pass
                toggle_server()

        new_min_delta = 1 / float(frame_rate_field.get())
        if new_min_delta != sett.minimum_frame_delta:
            sett.minimum_frame_delta = new_min_delta
            frame_loop_thread.minimum_frame_delta = new_min_delta
            sett.updated = True

        if sett.updated:
            save_settings(sett)
            sett.updated = False

        settings_screen.destroy()

    save_btn = tk.Button(settings_screen, text='Save', command=save, width=7)
    save_btn.grid(row=3, column=1, padx=5, pady=7, sticky='W')


def on_close():
    # if server active, disable
    if active_socket is not None:
        toggle_server()
    frame_loop_thread.cancel.set()
    cap.release()
    root.after(int(settings.minimum_frame_delta * 1000) + 10, root.destroy)


# TODO Temporary
def find_backend_library(x):
    return 'libusb\libusb-1.0.dll'


os.environ['PYUSB_DEBUG']="debug"
if __name__ == '__main__':

    backend = get_backend(find_library=find_backend_library)
    devices = find(find_all=1, custom_match=FindDevices([0x0E, 0x10]), backend=backend)
    device = list(devices)[0]
    print(device)
    # print(usb.util.get_string(camera, 5, 0x0000))
    # available_cameras: list[Tuple[int, str]] = []
    
    # for camera in list(cameras):
    #     print(camera.bNumConfigurations)

    max_image_width = 800
    max_image_height = 600

    frame_buffer = FrameBuffer()
    try:
        with open('./empkam_settings.json', 'r') as settings_file:
            settings_dict = json.load(settings_file)
            settings = Settings(**settings_dict)
    except FileNotFoundError:
        settings = Settings(server_port=8000, minimum_frame_delta=0.1)
        save_settings(settings)

    active_socket = None
    active_server_threads: list[ServerThread] = []

    root = tk.Tk()
    root.title('EmpKam')

    label = tk.Label(root)
    label.configure(width=800, height=600)
    label.grid(row=0, column=0)

    cap = cv2.VideoCapture(0)  # TODO allow user to switch active camera
    frame_loop_thread = FrameLoop(cap, frame_buffer, label, settings.minimum_frame_delta)
    frame_loop_thread.start()

    lower_pane = tk.Frame()

    inactive_status_img = ImageTk.PhotoImage(Image.open('./serv_status/inactive.png').resize((160, 40)))
    active_status_img = ImageTk.PhotoImage(Image.open('./serv_status/active.png').resize((160, 40)))

    serv_status = tk.Label(lower_pane, image=inactive_status_img, height=50)
    serv_status.grid(row=0, column=0)

    serv_toggle = tk.Button(lower_pane, command=toggle_server, text="Start Server")
    serv_toggle.grid(row=1, column=0, padx=25)

    settings_btn = tk.Button(lower_pane, text="Settings...", command=lambda: open_settings_screen(settings))
    settings_btn.grid(row=1, column=1, padx=25)

    lower_pane.grid(row=1, column=0)

    root.protocol("WM_DELETE_WINDOW", on_close)

    root.geometry(f"{max_image_width}x{max_image_height + 100}")
    root.resizable(False, False)
    root.mainloop()
    pass
