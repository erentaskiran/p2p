from DiscoverPeers import DiscoverPeers
import threading
import time
import socket
import asyncio
import websockets
from FileManager import FileServer, FileClient

class P2PNode:
    def __init__(self, port: int = 5003, web_socket_port: int = 8765):
        self.port = port
        self.web_socket_port = web_socket_port

        self.peers = []  
        self.files = []  
        self.files = self.list_all_file_paths("paylasilacak_dosyalar")

        self.peer_discovery = DiscoverPeers(self.port)

        # FileManager'ı entegre et
        self.file_server = FileServer(host="localhost", port=5001)  # Dosya sunucusunu başlat
        self.file_client = FileClient(ip="localhost", port=5002)     # Dosya istemcisini başlat

        self.web_socket_thread = threading.Thread(target=self.run_websocket_server, daemon=True)
        self.web_socket_thread.start()


        threading.Thread(target=self.peer_discovery.start_discovery, daemon=True).start()

        # FileServer'ı başka bir thread'de çalıştır
        self.file_server_thread = threading.Thread(target=self.file_server.start_server, daemon=True)
        self.file_server_thread.start()

        print("P2P Node initialized")
        print(f"P2P Node started on port {port}")
    
    def get_normalized_ip(self, ip_address):
        """IPv6 localhost adresini IPv4 localhost adresine çeviren yardımcı fonksiyon"""
        if ip_address == "::1" or ip_address == "0:0:0:0:0:0:0:1":
            return "localhost"  # veya "127.0.0.1" kullanabilirsiniz
        return ip_address

    def run_websocket_server(self):
        """WebSocket server'ı başlatan fonksiyon"""
        asyncio.run(self.start_websocket_server())

    async def start_websocket_server(self):
        """WebSocket server'ı başlatan fonksiyon"""
        print(f"WebSocket server starting on port {self.web_socket_port}...")
        async with websockets.serve(self.echo, "localhost", self.web_socket_port):
            await asyncio.Future()  # run forever


    async def echo(self, websocket):
        """WebSocket mesajlarını işleyen fonksiyon"""
        try:
            async for message in websocket:
                print(f"Received message: {message}")

                if message.startswith("receive_file:"):
                    filename = message.split(":")[1]
                    self.receive_file_from_peer(filename)
                else:
                    print(f"Unknown command: {message}")
                    # Echo the message back to the client

                await websocket.send(f"Echo: {message}")
        except websockets.exceptions.ConnectionClosed:
            print("WebSocket connection closed")

    def receive_file_from_peer(self, filename):
        """Dosya alma fonksiyonu"""
        ips = self.peer_discovery.list_of_peer_accordingly_to_ips(self.files)

    def list_all_file_paths(self, directory):
        file_names = []
        for root, dirs, files in os.walk(directory):
            for file in files:
                file_names.append(file)
        return file_names
