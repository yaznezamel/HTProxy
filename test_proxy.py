import urllib.request
import urllib.error
import concurrent.futures
import time

def fetch_url(url, data=None):
    try:
        req = urllib.request.Request(url, data=data, method='POST' if data else 'GET')
        with urllib.request.urlopen(req) as response:
            return response.status, response.read().decode('utf-8')
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode('utf-8')
    except Exception as e:
        return 0, str(e)

def main():
    url = "http://localhost:8000"
    num_requests = 20

    print(f"Sending {num_requests} concurrent requests to {url}...")

    start_time = time.time()

    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=num_requests) as executor:
        futures = [executor.submit(fetch_url, url, f"Payload {i}".encode('utf-8')) for i in range(num_requests)]
        for future in concurrent.futures.as_completed(futures):
            results.append(future.result())

    end_time = time.time()

    print(f"Completed in {end_time - start_time:.2f} seconds.")

    status_counts = {}
    for status, content in results:
        status_counts[status] = status_counts.get(status, 0) + 1

    print(f"Status counts: {status_counts}")

    for status, content in results[:5]:
        print(f"Sample response ({status}): {content[:100]}")

if __name__ == "__main__":
    main()
