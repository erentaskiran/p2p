from DiscoverPeers import DiscoverPeers
import threading
import time
import socket
import asyncio
import websockets
from FileManager import FileServer, FileClient
import hashlib
import os


class P2PNode:
    def __init__(self, port: int = 5003, web_socket_port: int = 8765):
        self.port = port
        self.web_socket_port = web_socket_port

        self.peers = []  
        self.files = {}  
        self.files = self.list_all_files("paylasilacak_dosyalar")

        # DiscoverPeers'ı self.files ile başlat
        self.peer_discovery = DiscoverPeers(self.port, self.files)

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
                    self.receive_file_from_peer(filename) # Updated call due to signature change
                else:
                    print(f"Unknown command: {message}")
                    # Echo the message back to the client

                await websocket.send(f"Echo: {message}")
        except websockets.exceptions.ConnectionClosed:
            print("WebSocket connection closed")

    # Eski imza: def receive_file_from_peer(self, filename, files)
    def receive_file_from_peer(self, requested_filename: str):
        """
        İstenilen dosyayı ağdaki bir peer'dan alır.
        Bu fonksiyon, DiscoverPeers sınıfında `find_file_source(filename)` gibi bir metodun
        var olduğunu varsayar (bu metod peer_ip, file_hash döndürmelidir).
        Ayrıca, `receive_file(peer_ip, file_hash, destination_path)` metodunun dosyayı
        belirtilen yola indirdiğini varsayar.
        """
        print(f"İstenen dosyayı alma denemesi: {requested_filename}")

        # find_file_source metodu DiscoverPeers.py içinde uygulandı.
        source_info = self.peer_discovery.find_file_source(requested_filename)

        if source_info and source_info[0] and source_info[1]:
            peer_ip, file_hash_on_peer = source_info
            print(f"Dosya bulundu: {requested_filename} (hash: {file_hash_on_peer}) peer üzerinde: {peer_ip}")

            download_directory = "indirilen_dosyalar" # İndirilen dosyalar için klasör adı
            # İndirme dizininin var olduğundan emin olun
            if not os.path.exists(download_directory):
                try:
                    os.makedirs(download_directory)
                    print(f"Dizin oluşturuldu: {download_directory}")
                except OSError as e:
                    print(f"Dizin oluşturulamadı {download_directory}: {e}")
                    return # İndirme dizini olmadan devam edilemez

            destination_path = os.path.join(download_directory, requested_filename)

            print(f"{peer_ip} adresinden {requested_filename} dosyası {destination_path} konumuna isteniyor")
            
            # `self.peer_discovery.receive_file` çağrısındaki üçüncü argüman `self.files` (bir dict) idi,
            # bu bir hedef yolu için yanlıştır. Düzeltilmiş çağrı:
            try:
                success = self.peer_discovery.receive_file(peer_ip, file_hash_on_peer, destination_path)
                if success:
                    print(f"{requested_filename} başarıyla alındı ve {destination_path} konumuna kaydedildi.")
                    # İsteğe bağlı: İndirilen dosyayı yerel paylaşılan dosyalara ekle
                    # new_file_hash = self.hash_file(destination_path)
                    # self.files[new_file_hash] = destination_path
                    # print(f"{requested_filename} yerel dosyalara eklendi ve paylaşıma açıldı.")
                else:
                    print(f"{requested_filename} dosyası {peer_ip} adresinden alınamadı.")
            except Exception as e:
                print(f"{requested_filename} dosyası {peer_ip} adresinden alınırken hata oluştu: {e}")
        else:
            print(f"{requested_filename} dosyası ağda bulunamadı.")

    def list_all_files(self, directory):
        files = {}
        for root, _, filenames in os.walk(directory):
            for filename in filenames:
                file_path = os.path.join(root, filename)
                tmp = self.hash_file(file_path)
                files[tmp] = file_path
        return files

    def hash_file(self, filepath):
        sha256_hash = hashlib.sha256()

        with open(filepath, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)

        return sha256_hash.hexdigest()
