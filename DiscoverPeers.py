import socket
import json
import netifaces
from typing import List, Dict
import threading

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

        try:
            interfaces = netifaces.interfaces()
            for interface in interfaces:
                ifaddresses = netifaces.ifaddresses(interface)
                if netifaces.AF_INET in ifaddresses:
                    for link in ifaddresses[netifaces.AF_INET]:
                        if 'broadcast' in link:
                            broadcast_ip = link['broadcast']
                            self.discovery_socket.sendto(
                                json.dumps(message).encode(),
                                (broadcast_ip, self.port)
                            )
            print("Broadcasting discovery message to local network.")
        except Exception as e:
            print(f"Error broadcasting discovery message: {e}")

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
        #
        while True:
            self.discover_peers()
            threading.Event().wait(5) 
