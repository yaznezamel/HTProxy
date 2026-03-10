import threading
import time
import logging
from http.server import BaseHTTPRequestHandler, HTTPServer
from concurrent.futures import ThreadPoolExecutor
import multiprocessing
import hashlib
import uuid
import time as time_mod

logger = logging.getLogger(__name__)
file_handler = logging.FileHandler("app.log")
logger.addHandler(file_handler)
logger.setLevel(logging.INFO)

class TokenBucket:
    def __init__(self, capacity, fill_rate):
        self.capacity = capacity
        self.fill_rate = fill_rate
        self.tokens = capacity
        self.last_fill = time.time()
        self.lock = threading.Lock()

    def consume(self, tokens=1):
        with self.lock:
            now = time.time()
            elapsed = now - self.last_fill
            self.tokens = min(self.capacity, self.tokens + elapsed * self.fill_rate)
            self.last_fill = now

            if self.tokens >= tokens:
                self.tokens -= tokens
                return True
            return False

user_buckets = {}
bucket_lock = threading.Lock()

def get_bucket(ip):
    with bucket_lock:
        if ip not in user_buckets:
            user_buckets[ip] = TokenBucket(capacity=5, fill_rate=5)
        return user_buckets[ip]

def cpu_heavy_worker(task_queue, result_queue):
    while True:
        try:
            batch = task_queue.get()
            if batch is None:
                break

            results = []
            for req_id, payload in batch:
                # Simulate CPU heavy task (e.g. hashing)
                res = payload
                for _ in range(10000):
                    res = hashlib.sha256(res.encode('utf-8')).hexdigest()
                results.append((req_id, res))

            result_queue.put(results)
        except Exception as e:
            logger.error(f"Worker error: {e}")

batch_queue = []
batch_lock = threading.Lock()
batch_condition = threading.Condition(batch_lock)
pending_requests = {}
pending_requests_lock = threading.Lock()

def batcher_thread_func(task_queue, batch_size=8, timeout=0.05):
    while True:
        with batch_condition:
            while len(batch_queue) == 0:
                batch_condition.wait()

            # We have at least 1 item. Wait until we have batch_size, or timeout expires.
            start_wait = time_mod.time()
            while len(batch_queue) < batch_size:
                elapsed = time_mod.time() - start_wait
                remaining = timeout - elapsed
                if remaining <= 0:
                    break
                batch_condition.wait(remaining)

            if len(batch_queue) > 0:
                batch_to_send = batch_queue[:batch_size]
                del batch_queue[:batch_size]
                task_queue.put(batch_to_send)

def result_monitor_thread_func(result_queue):
    while True:
        try:
            results = result_queue.get()
            if results is None:
                break

            for req_id, res in results:
                with pending_requests_lock:
                    if req_id in pending_requests:
                        event, result_box = pending_requests[req_id]
                        result_box.append(res)
                        event.set()
        except Exception as e:
            logger.error(f"Monitor error: {e}")

class ThreadPoolHTTPServer(HTTPServer):
    def __init__(self, server_address, RequestHandlerClass, max_workers=100):
        super().__init__(server_address, RequestHandlerClass)
        self.executor = ThreadPoolExecutor(max_workers=max_workers)

    def process_request(self, request, client_address):
        self.executor.submit(self._process_request_thread, request, client_address)

    def _process_request_thread(self, request, client_address):
        try:
            self.finish_request(request, client_address)
        except Exception:
            self.handle_error(request, client_address)
        finally:
            self.shutdown_request(request)

    def server_close(self):
        super().server_close()
        self.executor.shutdown(wait=True)

class ProxyHTTPRequestHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.handle_request("")

    def do_POST(self):
        content_length = int(self.headers.get('Content-Length', 0))
        post_data = self.rfile.read(content_length).decode('utf-8')
        self.handle_request(post_data)

    def handle_request(self, payload):
        client_ip = self.client_address[0]
        bucket = get_bucket(client_ip)

        if not bucket.consume(1):
            self.send_response(429)
            self.end_headers()
            self.wfile.write(b"Too Many Requests")
            return

        req_id = str(uuid.uuid4())
        event = threading.Event()
        result_box = []

        with pending_requests_lock:
            pending_requests[req_id] = (event, result_box)

        with batch_condition:
            batch_queue.append((req_id, payload))
            batch_condition.notify_all()

        # Wait for the result from the multiprocessing workers
        try:
            event.wait()
        finally:
            with pending_requests_lock:
                if req_id in pending_requests:
                    del pending_requests[req_id]

        if result_box:
            final_result = result_box[0]
            self.send_response(200)
            self.send_header('Content-type', 'text/plain')
            self.end_headers()
            self.wfile.write(f"Success: {final_result}".encode('utf-8'))
        else:
            self.send_response(500)
            self.end_headers()
            self.wfile.write(b"Internal Server Error")

def main():
    # Setup multiprocessing queues
    task_queue = multiprocessing.Queue()
    result_queue = multiprocessing.Queue()

    # Start CPU heavy workers
    num_processes = multiprocessing.cpu_count()
    workers = []
    for _ in range(num_processes):
        p = multiprocessing.Process(target=cpu_heavy_worker, args=(task_queue, result_queue))
        p.daemon = True
        p.start()
        workers.append(p)

    # Start batcher thread
    batcher_thread = threading.Thread(target=batcher_thread_func, args=(task_queue,), daemon=True)
    batcher_thread.start()

    # Start result monitor thread
    monitor_thread = threading.Thread(target=result_monitor_thread_func, args=(result_queue,), daemon=True)
    monitor_thread.start()

    server_address = ('', 8000)
    httpd = ThreadPoolHTTPServer(server_address, ProxyHTTPRequestHandler)
    print("Server started on port 8000...")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        httpd.server_close()
        print("Server stopped.")
        
        # Cleanup
        for _ in range(num_processes):
            task_queue.put(None)
        result_queue.put(None)
        for p in workers:
            p.join(timeout=1)

if __name__ == '__main__':
    main()
