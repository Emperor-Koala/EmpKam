# Credit: https://www.codeinsideout.com/blog/pi/stream-picamera-mjpeg/

from http.server import SimpleHTTPRequestHandler
import frame_buffer as fb


class StreamingHandler(SimpleHTTPRequestHandler):

    def __init__(self, frame_buffer: fb.FrameBuffer, *args):
        self.frame_buffer = frame_buffer
        super().__init__(*args)

    def do_GET(self):
        if self.path == '/snapshot.jpg':
            self.send_response(200)
            self.send_header('Age', '0')
            self.send_header('Cache-Control', 'no-cache, private')
            self.send_header('Pragma',  'no-cache')
            self.send_header('Content-Type', 'image/jpeg')
            self.end_headers()
            with self.frame_buffer.condition:
                self.frame_buffer.condition.wait()
                frame = self.frame_buffer.frame
                self.wfile.write(frame)
        elif self.path == '/stream.mjpg':
            # response
            self.send_response(200)
            # header
            self.send_header('Age', '0')
            self.send_header('Cache-Control', 'no-cache, private')
            self.send_header('Pragma', 'no-cache')
            self.send_header('Content-Type', 'multipart/x-mixed-replace; boundary=FRAME')
            self.end_headers()
            try:
                while self.server.running:
                    with self.frame_buffer.condition:
                        # wait for a new frame
                        self.frame_buffer.condition.wait()
                        frame = self.frame_buffer.frame
                        self.wfile.write(b'--FRAME\r\n')
                        self.send_header('Content-Type', 'image/jpeg')
                        self.send_header('Content-Length', str(len(frame)))
                        self.end_headers()
                        self.wfile.write(frame)
                        self.wfile.write(b'\r\n')
            except Exception as e:
                print(str(e))
        else:
            super().do_GET()
