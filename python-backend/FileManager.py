import socket
import os
import threading

class FileServer:
    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.running = False
        self.server = None
        # Determine the base directory for public files, relative to this script file
        script_dir = os.path.dirname(os.path.abspath(__file__))
        self.public_files_dir = os.path.abspath(os.path.join(script_dir, "publicFiles"))
        
        # You might want to ensure this directory exists or create it:
        # if not os.path.isdir(self.public_files_dir):
        #     os.makedirs(self.public_files_dir, exist_ok=True)
        # print(f"FileServer: Serving files from '{self.public_files_dir}'")

    def send_file(self, requested_filename, conn):
        # Basic sanitization: prevent directory traversal and absolute paths in client request
        if ".." in requested_filename or requested_filename.startswith('/') or requested_filename.startswith('\\'):
            error_msg = b"ERROR: Invalid filename."
            conn.sendall(error_msg)
            print(f"FileServer: Denied invalid filename request: '{requested_filename}'")
            return

        # Construct the full, absolute path to the intended file
        # os.path.join is important for platform-independent path construction
        prospective_path = os.path.join(self.public_files_dir, requested_filename)
        abs_file_path = os.path.abspath(prospective_path)

        # Security check: Ensure the public_files_dir exists and is a directory
        if not os.path.isdir(self.public_files_dir):
            error_msg = b"ERROR: Server configuration issue (public directory not found)."
            conn.sendall(error_msg)
            print(f"FileServer: Error - Public files directory not found or not a directory: '{self.public_files_dir}'")
            return
            
        # Security check: Ensure the resolved path is within the self.public_files_dir
        # Appending os.sep ensures that /publicFilesFoo does not match /publicFiles
        if not abs_file_path.startswith(self.public_files_dir + os.sep) and abs_file_path != self.public_files_dir:
            error_msg = b"ERROR: Access denied."
            conn.sendall(error_msg)
            print(f"FileServer: Denied access to '{abs_file_path}' (not within '{self.public_files_dir}')")
            return

        if not os.path.isfile(abs_file_path):
            error_msg = b"ERROR: File not found."
            conn.sendall(error_msg)
            print(f"FileServer: File not found at '{abs_file_path}'")
            return

        try:
            with open(abs_file_path, 'rb') as f:
                while chunk := f.read(1024):
                    conn.sendall(chunk)
            print(f"FileServer: Successfully sent file '{abs_file_path}'")
        except IOError as e:
            # Handle potential I/O errors during file read/send
            print(f"FileServer: IOError sending file '{abs_file_path}': {e}")
            conn.sendall(b"ERROR: Could not read or send file.")
        except Exception as e:
            print(f"FileServer: Unexpected error sending file '{abs_file_path}': {e}")
            conn.sendall(b"ERROR: Server error while sending file.")

    def start_server(self):
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.bind((self.host, self.port))
        self.server.listen(5)  # Allow 5 queued connections
        self.server.settimeout(1.0)  # Set timeout for non-blocking accept
        print("Dosya sunucusu başlatıldı...")
        
        self.running = True
        
        while self.running:
            try:
                conn, addr = self.server.accept()
                print("Bağlantı geldi:", addr)
                
                requested_file = conn.recv(1024).decode()
                print("İstenen dosya:", requested_file)
                
                self.send_file(requested_file, conn)
                conn.close()
            except socket.timeout:
                # This is just to allow the loop to check self.running periodically
                continue
            except Exception as e:
                print(f"Dosya sunucusu hatası: {e}")
    
    def stop_server(self):
        self.running = False
        if self.server:
            self.server.close()
        print("Dosya sunucusu durduruldu.")

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