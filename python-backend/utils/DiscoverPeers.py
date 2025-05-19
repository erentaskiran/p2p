import socket
import json
import netifaces
from typing import List, Dict
import threading
import time
import pathlib
import os
import logging
import base64
import hashlib
import time

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class DiscoverPeers:
    def __init__(self, port: int):
        self.discovery_target_port = port 
        self.port = port 
        self.discovery_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.discovery_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        self.discovery_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            self.discovery_socket.bind(('0.0.0.0', self.port))
        except OSError as e:
            logger.error(f"Error binding discovery socket to {self.port}: {e}. Trying random port.")
            self.discovery_socket.bind(('0.0.0.0', 0))
            self.port = self.discovery_socket.getsockname()[1]
            logger.info(f"Bound to new port: {self.port}. Discovery broadcasts will still target: {self.discovery_target_port}")

        self.peers: List[str] = []
        self.discovery_socket.settimeout(1.0)

    def discover_peers(self):
        
        logger.info("Starting peer discovery broadcast.")
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
                                    (broadcast_ip, self.discovery_target_port) 
                                )
                                logger.debug(f"Discovery message sent to {broadcast_ip}:{self.discovery_target_port}")
                            except Exception as send_err:
                                logger.warning(f"Error sending to {broadcast_ip}: {send_err}")
                logger.debug("Finished broadcasting discovery messages for this cycle.")
            except Exception as e:
                logger.error(f"Error during interface scan or broadcast: {e}", exc_info=True)
            time.sleep(2)

    def listen_for_peers(self):
        
        logger.info("Starting to listen for peers.")
        while True:
            try:
                data, addr = self.discovery_socket.recvfrom(1024)
                message = json.loads(data.decode())
                sender_ip = addr[0]
                sender_port = message.get('port', addr[1])
                logger.debug(f"Received message: {message} from {sender_ip}:{sender_port}")

                if message['type'] == 'discover':
                    response = {
                        'type': 'peer_info',
                        'port': self.port,
                    }
                    logger.info(f"Received discover from {sender_ip}:{sender_port}. Responding.")
                    self.discovery_socket.sendto(
                        json.dumps(response).encode(),
                        (sender_ip, sender_port)
                    )
                    peer_addr = f"{sender_ip}:{sender_port}"
                    if peer_addr not in self.peers:
                        self.peers.append(peer_addr)
                        logger.info(f"Peer added: {peer_addr}")

                elif message['type'] == 'peer_info':
                    peer_addr = f"{sender_ip}:{message['port']}"
                    if peer_addr not in self.peers:
                        self.peers.append(peer_addr)
                        logger.info(f"Discovered peer via peer_info: {peer_addr}")
                
                elif message['type'] == 'query_file':
                    requested_filename = message['filename']
                    sender_ip = addr[0]
                    original_sender_port = addr[1]
                    
                   
                    logger.info(f"Received query_file for '{requested_filename}' from {sender_ip}:{original_sender_port} (reply to port: {message.get('reply_port')})")
                    
                    found_file_hash = None
                    local_files = self.list_all_files("publicFiles")
                    for f_hash, f_path in local_files.items():
                        if os.path.basename(f_path) == requested_filename:
                            found_file_hash = f_hash
                            break
                    
                    if found_file_hash:
                        logger.info(f"File '{requested_filename}' found locally with hash {found_file_hash}. Responding.")
                        response = {
                            'type': 'file_found_response',
                            'filename': requested_filename,
                            'file_hash': found_file_hash,
                            'peer_ip': self.get_local_ip(),
                            'port': self.port            
                        }
                        
                       
                        reply_to_port = message.get('reply_port')
                        if reply_to_port:
                           
                            response_addr = (sender_ip, reply_to_port)
                            logger.debug(f"Sending file_found_response to {response_addr} (using reply_port from message)")
                        else:
                           
                           
                            response_addr = addr 
                            logger.warning(f"reply_port not found in query_file message from {sender_ip}. Responding to original sender port {original_sender_port}.")
                        
                        self.discovery_socket.sendto(json.dumps(response).encode(), response_addr)
                    else:
                        logger.info(f"File '{requested_filename}' not found locally.")

                elif message['type'] == "receive_file" and 'file_hash' in message:
                    file_hash_to_send = message['file_hash']
                    requester_ip = addr[0]
                   
                    requester_reply_port = message.get('port')

                    logger.info(f"Received 'receive_file' request for hash {file_hash_to_send} from {requester_ip}:{addr[1]}. Requester expects data on port {requester_reply_port}.")
                    
                    local_files = self.list_all_files("publicFiles")
                    if file_hash_to_send in local_files:
                        file_path_to_send = local_files[file_hash_to_send]
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

                            data_payload_bytes = json.dumps(data_message).encode()
                            payload_size = len(data_payload_bytes)
                            logger.info(f"Attempting to send file_data payload of size: {payload_size} bytes for {file_name_to_send} to {requester_ip}:{requester_reply_port}")
                            if payload_size > 60000:
                                logger.warning(f"Payload size {payload_size} for {file_name_to_send} is very large for a single UDP packet and may cause transmission failure. Consider implementing chunking for robust transfer.")

                            if requester_reply_port:
                               
                                reply_address = (requester_ip, requester_reply_port)
                                self.discovery_socket.sendto(data_payload_bytes, reply_address)
                                logger.info(f"Sent file data for {file_name_to_send} to {reply_address[0]}:{reply_address[1]}")
                            else:
                                logger.error(f"Cannot send file {file_name_to_send}: 'port' not specified in 'receive_file' message from {requester_ip}:{addr[1]}.")
                        except FileNotFoundError:
                            logger.error(f"File not found for sending: {file_path_to_send}")
                        except Exception as e:
                            logger.error(f"Error reading or sending file {file_path_to_send}: {e}", exc_info=True)
                    else:
                        logger.warning(f"Requested file hash {file_hash_to_send} not found in local files for sending.")

            except socket.timeout:
                continue
            except json.JSONDecodeError:
                logger.warning(f"Error decoding JSON from {addr[0] if 'addr' in locals() else 'unknown'}. Data: {data if 'data' in locals() else 'N/A'}")
            except Exception as e:
                logger.error(f"Error in listen_for_peers: {e}", exc_info=True)

    def start_discovery(self):
        
        logger.info("Initializing discovery threads.")
        threading.Thread(target=self.listen_for_peers, daemon=True).start()

        threading.Thread(target=self.discover_peers, daemon=True).start()

    def list_of_peer_accordingly_to_ips(self, file_name, files) -> List[str]:
        
        
        
        logger.warning("list_of_peer_accordingly_to_ips is likely deprecated or needs rework.")
        return ("", "")

    def find_file_source(self, requested_filename: str) -> tuple[str | None, int | None, str | None]:
        
        logger.info(f"Searching for file source: {requested_filename}")

        response_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        response_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            response_socket.bind(('0.0.0.0', 0))
        except Exception as e:
            logger.error(f"Error binding temporary response socket for find_file_source: {e}", exc_info=True)
            response_socket.close()
            return None, None, None
            
        reply_to_port = response_socket.getsockname()[1]
        logger.debug(f"find_file_source listening for response on temporary port {reply_to_port}")

        message = {
            'type': 'query_file',
            'filename': requested_filename,
            'reply_port': reply_to_port
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
            logger.error(f"Error getting broadcast addresses: {e}. Using 255.255.255.255.", exc_info=True)
            broadcast_addresses.append("255.255.255.255")

        if not broadcast_addresses:
             logger.warning("No broadcast addresses found by netifaces, using 255.255.255.255 as a fallback.")
             broadcast_addresses.append("255.255.255.255")
        
        logger.info(f"Attempting to broadcast file query to the following addresses: {list(set(broadcast_addresses))}")

        for bcast_ip in set(broadcast_addresses):
            try:
               
                self.discovery_socket.sendto(encoded_message, (bcast_ip, self.discovery_target_port))
                logger.debug(f"File query for '{requested_filename}' sent to {bcast_ip}:{self.discovery_target_port}, reply expected on port {reply_to_port}")
            except Exception as send_err:
                logger.warning(f"Error sending file query to {bcast_ip}: {send_err}")
        
        start_time = time.time()
        timeout_duration = 3
        
        response_socket.settimeout(0.5)

        try:
            while time.time() - start_time < timeout_duration:
                try:
                    data, addr = response_socket.recvfrom(1024)
                    response = json.loads(data.decode())
                    logger.debug(f"Received response while searching for file: {response} from {addr} on temp port {reply_to_port}")
                    
                    if response.get('type') == 'file_found_response' and \
                       response.get('filename') == requested_filename:
                        peer_ip = response.get('peer_ip', addr[0])
                        file_hash = response.get('file_hash')
                        peer_port = response.get('port')
                        if peer_port is None:
                            logger.warning(f"File_found_response from {peer_ip} for '{requested_filename}' did not include a port.")
                            return None, None, None 
                        logger.info(f"Found file '{requested_filename}' at {peer_ip}:{peer_port} with hash {file_hash}")
                        return peer_ip, peer_port, file_hash 
                except socket.timeout:
                    continue
                except json.JSONDecodeError:
                    logger.warning(f"JSON decode error while searching for file from {addr[0] if 'addr' in locals() else 'unknown'}")
                    continue
                except Exception as e:
                    logger.error(f"Error receiving file_found_response: {e}", exc_info=True)
                    continue
        finally:
            response_socket.close()
            logger.debug(f"Closed temporary response socket on port {reply_to_port} for find_file_source")

        logger.warning(f"File '{requested_filename}' not found on the network after {timeout_duration}s.")
        return None, None, None

    def query_peer_for_file(self, target_peer_address_str: str, requested_filename: str) -> tuple[str | None, int | None, str | None]:
        
        logger.info(f"Querying peer {target_peer_address_str} for file: {requested_filename}")
        
        try:
            target_ip, target_port_str = target_peer_address_str.split(':')
            target_port = int(target_port_str)
        except ValueError:
            logger.error(f"Invalid peer address format: {target_peer_address_str}. Expected IP:PORT")
            return None, None, None

        response_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        response_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            response_socket.bind(('0.0.0.0', 0))
        except Exception as e:
            logger.error(f"Error binding temporary response socket for query_peer_for_file: {e}", exc_info=True)
            response_socket.close()
            return None, None, None

        reply_to_port = response_socket.getsockname()[1]
        logger.debug(f"query_peer_for_file listening for response on temporary port {reply_to_port}")

        message = {
            'type': 'query_file',
            'filename': requested_filename,
            'reply_port': reply_to_port 
        }
        encoded_message = json.dumps(message).encode()

        try:
           
            self.discovery_socket.sendto(encoded_message, (target_ip, target_port))
            logger.debug(f"File query for '{requested_filename}' sent to {target_ip}:{target_port}, reply expected on port {reply_to_port}")
        except Exception as send_err:
            logger.warning(f"Error sending file query to {target_ip}:{target_port}: {send_err}")
            response_socket.close() 
            return None, None, None
        
        start_time = time.time()
        timeout_duration = 2  
        
        response_socket.settimeout(0.2)

        try:
            while time.time() - start_time < timeout_duration:
                try:
                    data, addr = response_socket.recvfrom(1024)
                    
                    if addr[0] == target_ip: 
                        response = json.loads(data.decode())
                        logger.debug(f"Received response while querying {target_peer_address_str}: {response} from {addr} on temp port {reply_to_port}")
                        
                        if response.get('type') == 'file_found_response' and \
                           response.get('filename') == requested_filename:
                            peer_ip_from_response = response.get('peer_ip', addr[0])
                            file_hash = response.get('file_hash')
                            peer_port_from_response = response.get('port') 
                            if peer_port_from_response is None:
                                logger.warning(f"File_found_response from {target_peer_address_str} for '{requested_filename}' did not include a port.")
                                return None, None, None
                            logger.info(f"Peer {target_peer_address_str} has file '{requested_filename}' (IP: {peer_ip_from_response}, Port: {peer_port_from_response}, Hash: {file_hash})")
                            return peer_ip_from_response, peer_port_from_response, file_hash 
                except socket.timeout:
                    continue
                except json.JSONDecodeError:
                    logger.warning(f"JSON decode error while querying {target_peer_address_str} from {addr[0] if 'addr' in locals() else 'unknown'}")
                    continue
                except Exception as e:
                    logger.error(f"Error receiving response from {target_peer_address_str}: {e}", exc_info=True)
                    break 
        finally:
            response_socket.close()
            logger.debug(f"Closed temporary response socket on port {reply_to_port} for query_peer_for_file")

        logger.info(f"File '{requested_filename}' not found on peer {target_peer_address_str} or no response.")
        return None, None, None

    def receive_file(self, peer_ip: str, peer_port: int, file_hash: str, destination_path: str) -> bool:
        logger.info(f"Requesting file with hash {file_hash} from {peer_ip}:{peer_port} to be saved at {destination_path}")

        response_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        response_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            response_socket.bind(('0.0.0.0', 0))
        except Exception as e:
            logger.error(f"Error binding temporary response socket for receive_file: {e}", exc_info=True)
            response_socket.close()
            return False
            
        reply_to_port = response_socket.getsockname()[1]
        logger.debug(f"receive_file listening for file data on temporary port {reply_to_port}")

        request_message = {
            'type': 'receive_file', 
            'file_hash': file_hash,
            'port': reply_to_port
        }
        
        try:
           
            self.discovery_socket.sendto(json.dumps(request_message).encode(), (peer_ip, peer_port))
            logger.debug(f"Sent 'receive_file' request to {peer_ip}:{peer_port} for hash {file_hash}, expecting data on port {reply_to_port}")
        except Exception as e:
            logger.error(f"Error sending file request to {peer_ip}:{peer_port}: {e}", exc_info=True)
            response_socket.close() 
            return False

        start_time = time.time()
        timeout_duration = 30
        
        response_socket.settimeout(2.0)

        try:
            while time.time() - start_time < timeout_duration:
                try:
                    data, addr = response_socket.recvfrom(65535) 
                    logger.debug(f"Received {len(data)} bytes from {addr} while waiting for file on temp port {reply_to_port}")
                    
                    if addr[0] != peer_ip:
                        logger.warning(f"Received data from unexpected IP {addr[0]} (expected {peer_ip}) while expecting file from {peer_ip} on port {reply_to_port}. Ignoring.")
                        continue

                    response = json.loads(data.decode())
                    logger.debug(f"Received message type: {response.get('type')} from {addr} on temp port {reply_to_port} for hash {file_hash}")

                    if response.get('type') == 'file_data' and response.get('file_hash') == file_hash:
                        logger.info(f"Received file_data for hash {file_hash} from {addr[0]}")
                        file_data_encoded = response.get('data')
                        
                        
                        try:
                            file_data_bytes = base64.b64decode(file_data_encoded)
                            os.makedirs(os.path.dirname(destination_path), exist_ok=True)
                            with open(destination_path, 'wb') as f:
                                f.write(file_data_bytes)
                            logger.info(f"File {destination_path} received and saved successfully.")
                            return True
                        except (base64.binascii.Error, TypeError) as b64_err:
                            logger.error(f"Base64 decode error for file {file_hash}: {b64_err}", exc_info=True)
                            return False
                        except IOError as io_err:
                            logger.error(f"IOError writing file {destination_path}: {io_err}", exc_info=True)
                            return False
                except socket.timeout:
                    continue
                except json.JSONDecodeError:
                    logger.warning(f"JSON decode error while receiving file data from {addr[0] if 'addr' in locals() else 'unknown'}")
                    continue
                except Exception as e:
                    logger.error(f"Error receiving file data: {e}", exc_info=True)
                    return False 
        finally:
            response_socket.close()
            logger.debug(f"Closed temporary response socket on port {reply_to_port} for receive_file")

        logger.warning(f"Timeout or error receiving file {file_hash} from {peer_ip}:{peer_port}.")
        return False

    def get_key_by_value(self,d, target_value_basename):
        
        for key, value_path in d.items():
            if os.path.basename(value_path) == target_value_basename:
                return key
        return None

    def get_local_ip(self):
        
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