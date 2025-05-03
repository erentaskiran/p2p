from DiscoverPeers import DiscoverPeers
import threading
import time
import socket
from FileManager import FileServer, FileClient

class P2PNode:
    def __init__(self, port: int = 5000, web_socket_port: int = 8765):
        self.port = port
        self.web_socket_port = web_socket_port

        self.peers = []  

        self.peer_discovery = DiscoverPeers(self.port)

        # FileManager'ı entegre et
        self.file_server = FileServer(host="localhost", port=5001)  # Dosya sunucusunu başlat
        self.file_client = FileClient(ip="localhost", port=5001)     # Dosya istemcisini başlat

        self.web_socket_thread = threading.Thread(target=self.start_websocket_server, daemon=True)
        self.web_socket_thread.start()

        threading.Thread(target=self.peer_discovery.discover_peers, daemon=True).start()

        # FileServer'ı başka bir thread'de çalıştır
        self.file_server_thread = threading.Thread(target=self.file_server.start_server, daemon=True)
        self.file_server_thread.start()

        print("P2P Node initialized")
        print(f"P2P Node started on port {port}")
        print(f"WebSocket server started on port {web_socket_port}")

    def start_websocket_server(self):
        """WebSocket server kodu buraya eklenebilir"""
        pass

    def stop(self):
        """WebSocket server'ı durdurma kodu buraya eklenebilir"""
        pass

    def send_file_to_peer(self, filename, peer_ip):
        """Dosya gönderme fonksiyonu"""
        print(f"Dosya {filename} {peer_ip} adresine gönderiliyor...")
        self.file_client.ip = peer_ip  # Peer IP adresini güncelle
        self.file_client.request_file(filename)
    
    def receive_file_from_peer(self, filename, peer_ip):
        """Dosya alma fonksiyonu"""
        print(f"Dosya {filename} {peer_ip} adresinden alınıyor...")
        self.file_server.host = peer_ip  # Peer IP adresini güncelle
        self.file_server.send_file(filename, self.file_server.server_socket)  # Sunucuya dosyayı gönder

if __name__ == "__main__":
    node = P2PNode(port=5000, web_socket_port=8765)
    try:
        while True:
            time.sleep(1)  
    except KeyboardInterrupt:
        print("P2P Node stopped")
