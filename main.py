from http.server import BaseHTTPRequestHandler, HTTPServer
import time
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
        self.wfile.write(b'Hello, world!')
        time.sleep(2)
        

# Main function to run the server
def main():
    # Define the server address and port
    server_address = ('', 8000)
    # Create an instance of the HTTP server
    httpd = HTTPServer(server_address, SimpleHTTPRequestHandler)
    print("Server started on port 8000…")
    # Start serving HTTP requests

    try: 
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("Closing application")

    finally:
        httpd.server_close()

if __name__ == '__main__':
    main()