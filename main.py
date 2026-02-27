import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from socketserver import ThreadingMixIn

# Define the HTTP request handler class
class SimpleHTTPRequestHandler(BaseHTTPRequestHandler):
# Override the do_GET method to handle GET requests
    def do_GET(self):
        # Set the response status code
        self.send_response(200)
        # Set the response headers
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        # Write the response content
        self.wfile.write(b"Hello, world!")

# Define a threaded HTTP server using ThreadingMixIn
class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    daemon_threads = True # Ensures threads exit when the server shuts down

# Main function to run the server
def main():
# Define the server address and port
    server_address = ('', 8000)
    # Create an instance of the threaded HTTP server
    httpd = ThreadedHTTPServer(server_address, SimpleHTTPRequestHandler)
    print("Server started on port 8000…")
    try:
    # Start serving HTTP requests
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        # Shutdown the server gracefully
        httpd.server_close()
        print("Server stopped.")



if __name__ == '__main__':
    main()