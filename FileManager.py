import socket
import os

class FileServer:
    def __init__(self, host, port):
        self.host = host
        self.port = port

    def send_file(self, filename, conn):
        if not os.path.isfile(filename):
            conn.sendall(b"ERROR: File not found.")
            return

        with open(filename, 'rb') as f:
            while chunk := f.read(1024):
                conn.sendall(chunk)

    def start_server(self):
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.bind((self.host, self.port))
        server.listen(1)
        print("Dosya sunucusu başlatıldı...")

        conn, addr = server.accept()
        print("Bağlantı geldi:", addr)

        requested_file = conn.recv(1024).decode()
        print("İstenen dosya:", requested_file)

        self.send_file(requested_file, conn)
        conn.close()

class FileClient:
    def __init__(self, ip, port):
        self.ip = ip
        self.port = port

    def request_file(self, filename):
        client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client.connect((self.ip, self.port))

        client.send(filename.encode()) 

        with open(f'received_{filename}', 'wb') as f:
            while True:
                data = client.recv(1024)
                if not data:
                    break
                if b"ERROR" in data:
                    print(data.decode()) 
                    break
                f.write(data)

        client.close()