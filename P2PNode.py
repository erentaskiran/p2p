from DiscoverPeers import DiscoverPeers
import threading
import time
import socket
import asyncio
import websockets
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

        # WebSocket sunucusunu başlat
        self.web_socket_thread = threading.Thread(target=self.run_websocket_server, daemon=True)
        self.web_socket_thread.start()

        threading.Thread(target=self.peer_discovery.discover_peers, daemon=True).start()

        # FileServer'ı başka bir thread'de çalıştır
        self.file_server_thread = threading.Thread(target=self.file_server.start_server, daemon=True)
        self.file_server_thread.start()

        print("P2P Node initialized")
        print(f"P2P Node started on port {port}")
        print(f"WebSocket server started on port {web_socket_port}")
    
    def get_normalized_ip(self, ip_address):
        """IPv6 localhost adresini IPv4 localhost adresine çeviren yardımcı fonksiyon"""
        if ip_address == "::1" or ip_address == "0:0:0:0:0:0:0:1":
            return "localhost"  # veya "127.0.0.1" kullanabilirsiniz
        return ip_address

    def run_websocket_server(self):
        """WebSocket server'ı başlatan fonksiyon"""
        asyncio.run(self.start_websocket_server())

    async def start_websocket_server(self):
        """WebSocket server başlatma fonksiyonu"""
        print(f"WebSocket server starting on port {self.web_socket_port}...")
        async with websockets.serve(self.echo, "localhost", self.web_socket_port):
            await asyncio.Future()  # run forever

    async def echo(self, websocket):
        """WebSocket mesajlarını işleyen fonksiyon"""
        try:
            async for message in websocket:
                print(f"Received message: {message}")

                if message.startswith("send_file:"):
                    filename = message.split(":")[1]
                    raw_ip = websocket.remote_address[0]
                    peer_ip = self.get_normalized_ip(raw_ip)
                    print(f"Raw peer IP: {raw_ip}, Normalized: {peer_ip}")
                    self.send_file_to_peer(filename, peer_ip)
                elif message.startswith("receive_file:"):
                    filename = message.split(":")[1]
                    raw_ip = websocket.remote_address[0]
                    peer_ip = self.get_normalized_ip(raw_ip)
                    print(f"Raw peer IP: {raw_ip}, Normalized: {peer_ip}")
                    self.receive_file_from_peer(filename, peer_ip)
                else:
                    print(f"Unknown command: {message}")
                    # Echo the message back to the client


                await websocket.send(f"Echo: {message}")
        except websockets.exceptions.ConnectionClosed:
            print("WebSocket connection closed")

    def stop(self):
        """WebSocket server'ı durdurma kodu buraya eklenebilir"""
        pass

    def send_file_to_peer(self, filename, peer_ip):
        """Dosya gönderme fonksiyonu"""
        print(f"Dosya {filename} {peer_ip} adresine gönderiliyor...")
        self.file_client.ip = peer_ip  # Peer IP adresini güncelle
        print(f"Peer IP: {self.file_client.ip}")
        self.file_client.request_file(filename)
    
    def receive_file_from_peer(self, filename, peer_ip):
        """Dosya alma fonksiyonu"""
        print(f"Dosya {filename} {peer_ip} adresinden alınıyor...")
        # Peer bilgisini güncelle ama socket işlemini FileClient üzerinden yapmamız gerekir
        # self.file_server.host = peer_ip  # Bu satır gerekli değil
        # self.file_server.send_file() yerine file_client'ı kullanalım
        self.file_client.ip = peer_ip  # Peer IP adresini güncelle
        self.file_client.request_file(filename)  # Dosyayı iste

if __name__ == "__main__":
    node = P2PNode(port=5000, web_socket_port=8765)
    try:
        while True:
            time.sleep(1)  
    except KeyboardInterrupt:
        print("P2P Node stopped")
