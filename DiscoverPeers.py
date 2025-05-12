import socket
import json
import netifaces
from typing import List, Dict
import threading
import time
import pathlib
import os

class DiscoverPeers:
    def __init__(self, port: int, local_files: Dict[str, str]):
        self.port = port
        self.discovery_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.discovery_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        self.discovery_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            self.discovery_socket.bind(('0.0.0.0', port))
        except OSError as e:
            print(f"Error binding discovery socket: {e}. Trying random port.")
            self.discovery_socket.bind(('0.0.0.0', 0))
            self.port = self.discovery_socket.getsockname()[1]
            print(f"Bound to new port: {self.port}")

        self.peers: List[str] = []
        self.local_files = local_files
        self.discovery_socket.settimeout(1.0)

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
        """Listen for peer discovery and file query messages"""
        while True:
            try:
                data, addr = self.discovery_socket.recvfrom(1024)
                message = json.loads(data.decode())
                sender_ip = addr[0]
                sender_port = message.get('port', addr[1])

                if message['type'] == 'discover':
                    response = {
                        'type': 'peer_info',
                        'port': self.port,
                    }
                    print(f"Received discover from {sender_ip}:{sender_port}. Responding.")
                    self.discovery_socket.sendto(
                        json.dumps(response).encode(),
                        (sender_ip, sender_port)
                    )
                    peer_addr = f"{sender_ip}:{sender_port}"
                    if peer_addr not in self.peers:
                        self.peers.append(peer_addr)
                        print(f"Peer added: {peer_addr}")

                elif message['type'] == 'peer_info':
                    peer_addr = f"{sender_ip}:{message['port']}"
                    if peer_addr not in self.peers:
                        self.peers.append(peer_addr)
                        print(f"Discovered peer via peer_info: {peer_addr}")
                
                elif message['type'] == 'query_file':
                    requested_filename = message['filename']
                    print(f"Received query_file for '{requested_filename}' from {sender_ip}:{addr[1]}")
                    found_file_hash = None
                    for f_hash, f_path in self.local_files.items():
                        if os.path.basename(f_path) == requested_filename:
                            found_file_hash = f_hash
                            break
                    
                    if found_file_hash:
                        print(f"File '{requested_filename}' found locally with hash {found_file_hash}. Responding.")
                        response = {
                            'type': 'file_found_response',
                            'filename': requested_filename,
                            'file_hash': found_file_hash,
                            'peer_ip': self.get_local_ip(),
                            'port': self.port
                        }
                        self.discovery_socket.sendto(json.dumps(response).encode(), addr)
                    else:
                        print(f"File '{requested_filename}' not found locally.")

                elif message['type'] == "recieve_file" and 'file_hash' in message:
                    file_hash_to_send = message['file_hash']
                    if file_hash_to_send in self.local_files:
                        file_path_to_send = self.local_files[file_hash_to_send]
                        file_name_to_send = os.path.basename(file_path_to_send)
                        file_format = file_name_to_send.split('.')[-1] if '.' in file_name_to_send else ""
                        
                        try:
                            with open(file_path_to_send, 'rb') as f:
                                file_data_bytes = f.read()
                            
                            import base64
                            file_data_encoded = base64.b64encode(file_data_bytes).decode('utf-8')

                            data_message = {
                                'type': 'file_data',
                                'port': self.port,
                                'file_hash': file_hash_to_send,
                                'file_name': file_name_to_send,
                                'file_format': file_format,
                                'data': file_data_encoded
                            }
                            self.discovery_socket.sendto(json.dumps(data_message).encode(), addr)
                            print(f"Sent file data for {file_name_to_send} to {addr[0]}:{addr[1]}")
                        except Exception as e:
                            print(f"Error reading or sending file {file_path_to_send}: {e}")
                    else:
                        print(f"Requested file hash {file_hash_to_send} not found in local files.")

            except socket.timeout:
                continue
            except json.JSONDecodeError:
                print(f"Error decoding JSON from {addr[0] if 'addr' in locals() else 'unknown'}")
                if 'data' in locals(): print(f"Received data: {data}")
            except Exception as e:
                print(f"Error in listen_for_peers: {e}")
                import traceback
                traceback.print_exc()

    def start_discovery(self):
        """Start discovery in a separate thread"""
        threading.Thread(target=self.listen_for_peers, daemon=True).start()

        threading.Thread(target=self.discover_peers, daemon=True).start()

    def list_of_peer_accordingly_to_ips(self, file_name, files) -> List[str]:
        """
        DEPRECATED or needs rework. Use find_file_source for finding files.
        This method seems to try to find IPs for a file and also handle responses.
        It has potential bugs (undefined 'ips', tmpHash logic).
        """
        print("Warning: list_of_peer_accordingly_to_ips is likely deprecated or needs rework.")
        return ("", "")

    def find_file_source(self, requested_filename: str) -> tuple[str | None, str | None]:
        """Broadcasts a query for a file and returns the (IP, file_hash) of a peer that has it."""
        print(f"Searching for file: {requested_filename}")
        message = {
            'type': 'query_file',
            'filename': requested_filename,
            'reply_port': self.port
        }
        encoded_message = json.dumps(message).encode()

        broadcast_addresses = []
        try:
            interfaces = netifaces.interfaces()
            for interface in interfaces:
                ifaddresses = netifaces.ifaddresses(interface)
                inet_info = ifaddresses.get(netifaces.AF_INET, [])
                for link in inet_info:
                    broadcast_ip = link.get('broadcast')
                    if broadcast_ip:
                        broadcast_addresses.append(broadcast_ip)
        except Exception as e:
            print(f"Error getting broadcast addresses: {e}. Using 255.255.255.255.")
            broadcast_addresses.append("255.255.255.255")

        if not broadcast_addresses:
             broadcast_addresses.append("255.255.255.255")

        for bcast_ip in set(broadcast_addresses):
            try:
                self.discovery_socket.sendto(encoded_message, (bcast_ip, self.port))
                print(f"File query for '{requested_filename}' sent to {bcast_ip}:{self.port}")
            except Exception as send_err:
                print(f"Error sending file query to {bcast_ip}: {send_err}")
        
        start_time = time.time()
        timeout_duration = 3
        
        original_timeout = self.discovery_socket.gettimeout()
        self.discovery_socket.settimeout(0.5)

        try:
            while time.time() - start_time < timeout_duration:
                try:
                    data, addr = self.discovery_socket.recvfrom(1024)
                    response = json.loads(data.decode())
                    
                    if response.get('type') == 'file_found_response' and \
                       response.get('filename') == requested_filename:
                        peer_ip = response.get('peer_ip', addr[0])
                        file_hash = response.get('file_hash')
                        print(f"Found file '{requested_filename}' at {peer_ip} with hash {file_hash}")
                        return peer_ip, file_hash
                except socket.timeout:
                    continue
                except json.JSONDecodeError:
                    print(f"JSON decode error while searching for file from {addr[0] if 'addr' in locals() else 'unknown'}")
                    continue
                except Exception as e:
                    print(f"Error receiving file_found_response: {e}")
                    continue
        finally:
            self.discovery_socket.settimeout(original_timeout)

        print(f"File '{requested_filename}' not found on the network after {timeout_duration}s.")
        return None, None

    def receive_file(self, peer_ip: str, file_hash: str, destination_path: str) -> bool:
        """
        Requests a file from a specific peer and saves it to destination_path.
        This now handles receiving base64 encoded data.
        """
        print(f"Requesting file with hash {file_hash} from {peer_ip}:{self.port}")
        request_message = {
            'type': 'recieve_file',
            'file_hash': file_hash,
            'port': self.port
        }
        
        try:
            self.discovery_socket.sendto(json.dumps(request_message).encode(), (peer_ip, self.port))
        except Exception as e:
            print(f"Error sending file request to {peer_ip}: {e}")
            return False

        start_time = time.time()
        timeout_duration = 10
        
        original_timeout = self.discovery_socket.gettimeout()
        self.discovery_socket.settimeout(1.0)

        try:
            while time.time() - start_time < timeout_duration:
                try:
                    data, addr = self.discovery_socket.recvfrom(65535)
                    response = json.loads(data.decode())

                    if response.get('type') == 'file_data' and response.get('file_hash') == file_hash:
                        print(f"Received file_data for hash {file_hash} from {addr[0]}")
                        file_data_encoded = response.get('data')
                        
                        import base64
                        try:
                            file_data_bytes = base64.b64decode(file_data_encoded)
                            with open(destination_path, 'wb') as f:
                                f.write(file_data_bytes)
                            print(f"File {destination_path} received and saved successfully.")
                            return True
                        except (base64.binascii.Error, TypeError) as b64_err:
                            print(f"Base64 decode error for file {file_hash}: {b64_err}")
                            return False
                        except IOError as io_err:
                            print(f"IOError writing file {destination_path}: {io_err}")
                            return False
                except socket.timeout:
                    continue
                except json.JSONDecodeError:
                    print(f"JSON decode error while receiving file data from {addr[0] if 'addr' in locals() else 'unknown'}")
                    continue
                except Exception as e:
                    print(f"Error receiving file data: {e}")
                    return False
        finally:
            self.discovery_socket.settimeout(original_timeout)

        print(f"Timeout or error receiving file {file_hash} from {peer_ip}.")
        return False

    def get_key_by_value(self,d, target_value_basename):
        """Finds the first key in a dictionary whose filepath value has the target_value_basename."""
        for key, value_path in d.items():
            if os.path.basename(value_path) == target_value_basename:
                return key
        return None

    def get_local_ip(self):
        """Attempts to get a non-loopback local IP address."""
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.settimeout(0.1)
            try:
                s.connect(('10.255.255.255', 1))
                ip = s.getsockname()[0]
            except Exception:
                ip = '127.0.0.1'
            finally:
                s.close()
            return ip
        except Exception:
            return '127.0.0.1'