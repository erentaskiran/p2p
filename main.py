import threading
from P2PNode import P2PNode
from ManifestManager import ManifestManager
import time

def send_manifest_to_peers(node, manifest):
    if node.peers:
        for peer in node.peers:
            print(f"Sending manifest to {peer}")
            node.send_to_peer(peer, {
                "type": "file_manifest",
                "manifest": manifest
            })
            print(f"Manifest sent to {peer}")
    else:
        print("No peers discovered yet.")

if __name__ == "__main__":

    node = P2PNode()
    
    threading.Thread(target=node.peer_discovery.listen_for_peers, daemon=True).start()

    directory_path = "paylasilacak_dosyalar"
    manifest = ManifestManager.generate_manifest_for_directory(directory_path)

    if manifest:  
        print("Generated Manifest:", manifest)
        
        send_manifest_to_peers(node, manifest)
    else:
        print("No files found in the directory, manifest not generated.")

    try:
        while True:
            time.sleep(5)
    except KeyboardInterrupt:
        print("\nStopping P2P node...")
        node.stop()
