import zipfile
import os

zip_path = "models/_output_.zip"
extract_dir = "models"

if os.path.exists(zip_path):
    print(f"Extracting {zip_path} into {extract_dir}...")
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extractall(extract_dir)
    print("Extracted successfully!")
    
    # List contents of runs/
    runs_dir = os.path.join(extract_dir, "runs")
    if os.path.exists(runs_dir):
        print("Runs directory contents:", os.listdir(runs_dir))
