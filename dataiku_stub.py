# dataiku_stub.py
import os, csv
ROOT = os.path.dirname(__file__)
DATASETS_DIR = os.path.join(ROOT, "datasets")
FOLDERS_DIR = os.path.join(ROOT, "managed_folders")
def _ensure_dirs():
    os.makedirs(DATASETS_DIR, exist_ok=True)
    os.makedirs(FOLDERS_DIR, exist_ok=True)
class _Project:
    def list_datasets(self):
        _ensure_dirs()
        return [{"name": fn} for fn in os.listdir(DATASETS_DIR) if fn.lower().endswith(".csv")]
class _Client:
    def get_default_project(self):
        return _Project()
def api_client():
    return _Client()
class Dataset:
    def __init__(self, name):
        _ensure_dirs()
        self.path = os.path.join(DATASETS_DIR, name)
        if not os.path.isfile(self.path):
            raise FileNotFoundError(self.path)
    def read_schema(self):
        with open(self.path, "r", encoding="utf-8") as f:
            header = f.readline().strip("\n\r")
        if not header:
            return []
        import csv as _csv
        cols = next(_csv.reader([header]))
        return [{"name": c} for c in cols]
class Folder:
    def __init__(self, folder_id):
        _ensure_dirs()
        self.path = os.path.join(FOLDERS_DIR, folder_id)
        os.makedirs(self.path, exist_ok=True)
    def upload_data(self, name, data: bytes):
        with open(os.path.join(self.path, name), "wb") as f:
            f.write(data)
