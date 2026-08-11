import urllib.request
import os

urls = [
    "https://raw.githubusercontent.com/sspeedy99/Abandoned-Object-Detection/master/pets2006_3.mp4",
    "https://raw.githubusercontent.com/SaranshKejriwal/Abandoned_Object/master/aban3.mp4",
    "https://raw.githubusercontent.com/zebadoulathunnisa/Abandoned-Object-Detection-for-Intelligent-Video-Surveillance/main/cut.mp4",
]

os.makedirs("tests/clips", exist_ok=True)

for url in urls:
    filename = url.split("/")[-1]
    dest = os.path.join("tests/clips", filename)
    print(f"Downloading {url} -> {dest}...")
    try:
        urllib.request.urlretrieve(url, dest)
        size = os.path.getsize(dest)
        print(f"Downloaded {dest} successfully ({size} bytes)")
    except Exception as e:
        print(f"Failed to download {url}: {e}")
