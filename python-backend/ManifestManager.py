import os
import hashlib
import json
from typing import List, Dict
import socket
import threading

CHUNK_SIZE = 1024 * 1024 

class ManifestManager:
    @staticmethod
    def generate_file_manifest(file_path: str) -> Dict:
        file_size = os.path.getsize(file_path)
        chunk_count = (file_size + CHUNK_SIZE - 1) // CHUNK_SIZE
        
        sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            while chunk := f.read(8192):
                sha256.update(chunk)

        return {
            "filename": os.path.basename(file_path),
            "size": file_size,
            "sha256": sha256.hexdigest(),
            "chunk_count": chunk_count
        }

    @staticmethod
    def generate_manifest_for_directory(directory_path: str) -> List[Dict]:
        manifest: List[Dict] = []
        
        for root, dirs, files in os.walk(directory_path):
            for name in files:
                file_path = os.path.join(root, name)
                manifest_entry = ManifestManager.generate_file_manifest(file_path)
                manifest.append(manifest_entry)

        return manifest
