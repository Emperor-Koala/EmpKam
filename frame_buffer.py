# Credit: https://www.codeinsideout.com/blog/pi/stream-picamera-mjpeg/

import io
from threading import Condition


class FrameBuffer(object):
    def __init__(self):
        # store each frame
        self.frame = None
        # buffer to hold incoming frame
        self.buffer = io.BytesIO()
        # synchronize between threads
        self.condition = Condition()

    def write(self, buf):
        # if it's a JPEG image
        if buf.startswith(b'\xff\xd8'):
            with self.condition:
                # write to buffer
                self.buffer.seek(0)
                self.buffer.write(buf)
                # extract frame
                self.buffer.truncate()
                self.frame = self.buffer.getvalue()
                # notify other threads
                self.condition.notify_all()
