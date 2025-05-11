import socket
import json
import netifaces
from typing import List, Dict
import threading
import time
import pathlib
import os

class DiscoverPeers:
    def __init__(self, port: int):
        self.port = port
        self.discovery_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.discovery_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        self.discovery_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.discovery_socket.bind(('0.0.0.0', port))
        self.peers: List[str] = []  

    def discover_peers(self):
        """Broadcast discovery message to find other peers"""
        message = {
            'type': 'discover',
            'port': self.port
        }

        while True:
            try:
                interfaces = netifaces.interfaces()
                for interface in interfaces:
                    ifaddresses = netifaces.ifaddresses(interface)
                    inet_info = ifaddresses.get(netifaces.AF_INET, [])

                    for link in inet_info:
                        broadcast_ip = link.get('broadcast')
                        if broadcast_ip:
                            try:
                                self.discovery_socket.sendto(
                                    json.dumps(message).encode(),
                                    (broadcast_ip, self.port)
                                )
                                print(f"Discovery message sent to {broadcast_ip}:{self.port}")
                            except Exception as send_err:
                                print(f"Error sending to {broadcast_ip}: {send_err}")
                print("Finished broadcasting discovery messages.")
            except Exception as e:
                print(f"Error during interface scan or broadcast: {e}")
            time.sleep(2)

    def listen_for_peers(self):
        """Listen for peer discovery messages"""
        while True:
            try:
                data, addr = self.discovery_socket.recvfrom(1024)
                message = json.loads(data.decode())
                
                if message['type'] == 'discover':
                    response = {
                        'type': 'peer_info',
                        'port': self.port,
                        'ip': addr[0]  
                    }
                    self.discovery_socket.sendto(
                        json.dumps(response).encode(),
                        addr
                    )
                    print(f"Discovered peer at {addr[0]}:{message['port']}")
            
                    peer_addr = f"{addr[0]}:{message['port']}"
                    if peer_addr not in self.peers:
                        self.peers.append(peer_addr)
                        print(f"Peer added: {peer_addr}")
            except Exception as e:
                print(f"Discovery error: {e}")

    def start_discovery(self):
        """Start discovery in a separate thread"""
        threading.Thread(target=self.listen_for_peers, daemon=True).start()

        threading.Thread(target=self.discover_peers, daemon=True).start()

    def list_of_peer_accordingly_to_ips(self, file_name, files) -> List[str]:
        """List peers according to their IPs"""
        message = {
            'type': 'peer_file_info',
            'port': self.port,
            'file_name': file_name
        }

        ip = ""

        try:
            interfaces = netifaces.interfaces()
            for interface in interfaces:
                ifaddresses = netifaces.ifaddresses(interface)
                inet_info = ifaddresses.get(netifaces.AF_INET, [])

                for link in inet_info:
                    broadcast_ip = link.get('broadcast')
                    if broadcast_ip:
                        try:
                            self.discovery_socket.sendto(
                                json.dumps(message).encode(),
                                (broadcast_ip, self.port)
                            )
                            print(f"Discovery message sent to {broadcast_ip}:{self.port}")
                        except Exception as send_err:
                            print(f"Error sending to {broadcast_ip}: {send_err}")
        except Exception as e:
            print(f"Error during interface scan or broadcast: {e}")
        
        tmpHash = ""
        tm = time.time()
        while tm + 2 > time.time():
            try:
                data, addr = self.discovery_socket.recvfrom(1024)
                message = json.loads(data.decode())
                
                if message['type'] == 'peer_file_info':
                    if message['file_name'] in [file.rsplit('/', 1)[-1] for file in files.values()]:
                        response = {
                            'type': 'peer_file_info_answer',
                            'port': self.port,
                            'ip': addr[0],  
                            "file_hash": self.get_key_by_value(files, message['file_name'])
                        }
                        self.discovery_socket.sendto(
                            json.dumps(response).encode(),
                            addr
                        )
                        peer_addr = f"{addr[0]}:{message['port']}"
                        if peer_addr not in self.peers:
                            self.peers.append(peer_addr)
                            print(f"Peer added: {peer_addr}")
                elif message['type'] == 'peer_file_info_answer':
                    if message['file_hash'] == tmpHash:
                        ips.append(message['ip'])
                        tmpHash = message['file_hash']
                        break
            except Exception as e:
                print(f"Discovery error: {e}")
        return (ip, tmpHash)

    def receive_file(self, ip, fileHash, files):
        message = {
            'type': 'recieve_file',
            'port': self.port,
            'file_hash': fileHash
        } 

        try:
            self.discovery_socket.sendto(
                json.dumps(message).encode(),
                (ip, self.port)
            )
            print(f"File request sent to {ip}:{self.port}")
        except Exception as send_err:
            print(f"Error sending to {ip}: {send_err}")
        
        tm = time.time()
        while tm + 2 > time.time():
            try:
                data, addr = self.discovery_socket.recvfrom(1024)
                message = json.loads(data.decode())
                
                if message['type'] == 'file_data' and message['file_hash'] == fileHash:
                    fileFormat = message['file_format']
                    fileName = message['file_name']

                    with open(f"{fileName}.{fileFormat}", 'wb') as f:
                        f.write(message['data'].encode())
                    print(f"File received from {addr[0]}:{message['port']}")
                    break
                elif message['type'] == "recieve_file":
                    fileHash = message['file_hash']
                    fileName = files[fileHash]
                    fileFormat = fileName.split('.')[-1]
                    
                    with open(f"{fileName}", 'r') as f:
                        data = f.read()
                    message = {
                        'type': 'file_data',
                        'port': self.port,
                        'file_hash': fileHash,
                        'file_name': fileName.rsplit('/', 1)[-1],
                        'file_format': fileFormat,
                        'data': data
                    }
                    self.discovery_socket.sendto(
                        json.dumps(message).encode(),
                        (ip, self.port)
                    )
            except Exception as e:
                print(f"File receive error: {e}")

    def get_key_by_value(self,d, target_value):
        for key, value in d.items():
            if value == target_value:
                return key
        return None