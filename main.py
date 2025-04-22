import socket
import threading
import time
import json
from typing import List, Dict

class P2PNode:
    def __init__(self, port: int = 5000):
        self.port = port
        self.peers: List[str] = []
        self.running = True
        
        # Discovery socket for finding other peers
        self.discovery_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.discovery_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.discovery_socket.bind(('0.0.0.0', port))
        
        # Communication socket for peer-to-peer messaging
        self.comm_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.comm_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.comm_socket.bind(('0.0.0.0', port + 1))
        self.comm_socket.listen(5)
        
        # Start discovery and communication threads
        self.discovery_thread = threading.Thread(target=self._discovery_listener)
        self.comm_thread = threading.Thread(target=self._communication_listener)
        self.discovery_thread.start()
        self.comm_thread.start()
        
        print(f"P2P Node started on port {port}")
    
    def _discovery_listener(self):
        """Listen for peer discovery messages"""
        while self.running:
            try:
                data, addr = self.discovery_socket.recvfrom(1024)
                message = json.loads(data.decode())
                
                if message['type'] == 'discover':
                    # Send response with our information
                    response = {
                        'type': 'peer_info',
                        'port': self.port,
                        'ip': socket.gethostbyname(socket.gethostname())
                    }
                    self.discovery_socket.sendto(
                        json.dumps(response).encode(),
                        addr
                    )
                    
                    # Add new peer if not already in our list
                    peer_addr = f"{addr[0]}:{message['port']}"
                    if peer_addr not in self.peers:
                        self.peers.append(peer_addr)
                        print(f"Discovered new peer: {peer_addr}")
                
            except Exception as e:
                print(f"Discovery error: {e}")
    
    def _communication_listener(self):
        """Listen for peer-to-peer communication"""
        while self.running:
            try:
                client_socket, addr = self.comm_socket.accept()
                threading.Thread(
                    target=self._handle_peer_connection,
                    args=(client_socket,)
                ).start()
            except Exception as e:
                print(f"Communication error: {e}")
    
    def _handle_peer_connection(self, client_socket: socket.socket):
        """Handle incoming peer connections"""
        try:
            data = client_socket.recv(1024)
            message = json.loads(data.decode())
            print(f"Received message from peer: {message}")
        except Exception as e:
            print(f"Connection handling error: {e}")
        finally:
            client_socket.close()
    
    def discover_peers(self):
        """Broadcast discovery message to find other peers"""
        message = {
            'type': 'discover',
            'port': self.port
        }
        
        # Broadcast to all possible local network addresses
        for i in range(1, 255):
            try:
                self.discovery_socket.sendto(
                    json.dumps(message).encode(),
                    (f'192.168.1.{i}', self.port)
                )
            except Exception as e:
                pass
    
    def send_to_peer(self, peer_addr: str, message: Dict):
        """Send a message to a specific peer"""
        try:
            ip, port = peer_addr.split(':')
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect((ip, int(port) + 1))
            sock.send(json.dumps(message).encode())
            sock.close()
        except Exception as e:
            print(f"Error sending to peer {peer_addr}: {e}")
    
    def stop(self):
        """Stop the P2P node"""
        self.running = False
        self.discovery_socket.close()
        self.comm_socket.close()

if __name__ == "__main__":
    # Create a P2P node
    node = P2PNode()
    
    try:
        # Discover peers every 5 seconds
        while True:
            node.discover_peers()
            print(f"Current peers: {node.peers}")
            time.sleep(5)
    except KeyboardInterrupt:
        print("\nStopping P2P node...")
        node.stop()
