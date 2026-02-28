import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from socketserver import ThreadingMixIn
import time
import tracemalloc 
import logging



logger = logging.getLogger(__name__)
file_handler = logging.FileHandler("app.log")
logger.addHandler(file_handler)
logger.setLevel(logging.INFO)

TOKENS = 5
TOKEN_LOCK = threading.Lock()



# Define the HTTP request handler class
class SimpleHTTPRequestHandler(BaseHTTPRequestHandler):
# Override the do_GET method to handle GET requests
    def do_GET(self):
        global TOKENS  


        # only lock the shared state and separate the logic processing part
        with TOKEN_LOCK:
            if TOKENS > 0 :
                time.sleep(0.3)
                TOKENS -=1
                allowed = True
            else:
                allowed = False


        if allowed:
                self.send_response(200)
                # Set the response headers
                self.send_header('Content-type', 'text/html')
                self.end_headers()
                # Write the response content
                self.wfile.write(b"Hello, world!")
                logger.info(f"the value of tokens is {TOKENS}")
                time.sleep(1.5)



        else:
            self.send_response(429)
            self.end_headers()
            self.wfile.write(b"Too many requests - no tokens left")

# Define a threaded HTTP server using ThreadingMixIn
class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    daemon_threads = True # Ensures threads exit when the server shuts down

# Main function to run the server
def main():
# Define the server address and port
    tracemalloc.start()
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
        # --- NEW MEMORY PROFILING LOGIC ---
        print("[ System Memory Snapshot ]")
        snapshot = tracemalloc.take_snapshot()
        top_stats = snapshot.statistics('lineno')
        
        for stat in top_stats[:10]: # Print the top 10 memory consumers
            print(stat)



if __name__ == '__main__':
    main()