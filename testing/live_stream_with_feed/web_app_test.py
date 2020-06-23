from requests import get
import socketserver
from http import server


PORT = 5000  # port on which to host the stream

# html for the web browser stream
PAGE = """\
<html>
<head><title>Picam</title></head>
<body>
    <h1>RasPi MJPEG Streaming</h1>
    <img src="stream.mjpg" width="640" height="480" />
</body>
</html>
"""


class StreamingHandler(server.BaseHTTPRequestHandler):
    """ Passed into StreamingServer to handle requests """

    def do_INGEST_VIDEO(self):
        """ Handles stream from video client"""


    def do_GET(self):
        """ Handles stream requests from a web browser """
        ip, port = self.client_address
        print("Streaming to Web Browser ({}:{})".format(ip, port))

        # Set page headers based on location
        if self.path == '/':
            self.send_response(301)  # redirect
            self.send_header('Location', '/index.html')  # redirect to index.html
            self.end_headers()
        elif self.path == '/favicon.ico':
            self.send_response(200)  # success
            self.send_header('Content-Type', 'image/x-icon')  # favicon
            self.end_headers()
            with open('favicon.ico', 'rb') as fout:  # send favicon image
                self.wfile.write(fout.read())
        elif self.path == '/index.html':
            content = PAGE.encode('utf-8')  # encode html string
            self.send_response(200)  # success
            self.send_header('Content-Type', 'text/html')
            self.send_header('Content-Length', len(content))
            self.end_headers()
            self.wfile.write(content)  # write html content to page
        elif self.path == '/stream.mjpg':
            self.send_response(200)  # success
            self.send_header('Age', 0)
            self.send_header('Cache-Control', 'no-cache, private')
            self.send_header('Pragma', 'no-cache')
            self.send_header('Content-Type', 'multipart/x-mixed-replace; boundary=FRAME')
            self.end_headers()
            print("success")
        else:
            self.send_error(404)  # couldn't find it
            self.end_headers()


class StreamingServer(socketserver.ThreadingMixIn, server.HTTPServer):
    """ Server class that will call serve_forever() in collection.py """
    allow_reuse_address = True
    daemon_threads = True


try:
    address = ('', PORT)
    server = StreamingServer(address, StreamingHandler)
    ip = get('http://ipinfo.io/ip').text.replace('\n', '')
    print("Starting Server:  {}:{}".format(ip, PORT))
    server.serve_forever()  # start server
finally:
    print("done")
