import threading
from P2PNode import P2PNode
from ManifestManager import ManifestManager
import time

if __name__ == "__main__":

    node = P2PNode()
    
    directory_path = "paylasilacak_dosyalar"
    
    try:
        while True:
            time.sleep(5)
    except KeyboardInterrupt:
        print("\nStopping P2P node...")
        node.stop()