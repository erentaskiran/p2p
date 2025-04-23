from DiscoverPeers import DiscoverPeers
import threading
import time

class P2PNode:
    def __init__(self, port: int = 5000, web_socket_port: int = 8765):
        self.port = port
        self.web_socket_port = web_socket_port

        self.peers = []  

        self.peer_discovery = DiscoverPeers(self.port)

        self.web_socket_thread = threading.Thread(target=self.start_websocket_server, daemon=True)
        self.web_socket_thread.start()

        threading.Thread(target=self.peer_discovery.discover_peers, daemon=True).start()

        print("P2P Node initialized")

        print(f"P2P Node started on port {port}")
        print(f"WebSocket server started on port {web_socket_port}")

    def start_websocket_server(self):
        """WebSocket server kodu buraya eklenebilir"""  
        pass
    def stop(self):
        """WebSocket server'ı durdurma kodu buraya eklenebilir"""  
        pass

if __name__ == "__main__":
    node = P2PNode(port=5000, web_socket_port=8765)
    try:
        while True:
            time.sleep(1)  
    except KeyboardInterrupt:
        print("P2P Node stopped")
