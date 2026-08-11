import urllib.request
import os

urls = [
    "https://raw.githubusercontent.com/intel-iot-devkit/sample-videos/master/person-bicycle-car-detection.mp4",
    "https://github.com/intel-iot-devkit/sample-videos/raw/master/store-aisle-detection.mp4",
    "https://github.com/intel-iot-devkit/sample-videos/raw/master/bottle-detection.mp4",
]

os.makedirs("tests/clips", exist_ok=True)

for url in urls:
    filename = url.split("/")[-1]
    dest = os.path.join("tests/clips", filename)
    if not os.path.exists(dest):
        print(f"Downloading {url} -> {dest}...")
        try:
            urllib.request.urlretrieve(url, dest)
            print(f"Downloaded {dest} ({os.path.getsize(dest)} bytes)")
        except Exception as e:
            print(f"Failed to download {url}: {e}")
