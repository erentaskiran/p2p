import logging
from DiscoverPeers import DiscoverPeers
import threading
import time
from FileManager import FileServer, FileClient
import hashlib
import os
from websocket import run_server as run_websocket_server

# Configure basic logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class P2PNode:
    def __init__(self, port: int = 5003, web_socket_port: int = 8765):
        self.port = port
        self.web_socket_port = web_socket_port
        logger.info(f"Initializing P2PNode on port {port} with WebSocket port {web_socket_port}")

        self.peers = []
        self.files = {}
        self.files = self.list_all_files("publicFiles")
        logger.info(f"Indexed files: {self.files}")

        self.peer_discovery = DiscoverPeers(self.port, self.files)

        # FileManager integration (FileServer might be for a different protocol or direct TCP transfers)
        # If FileServer is for direct TCP and not WebSocket, it can remain.
        self.file_server = FileServer(host="localhost", port=5001) 
        self.file_client = FileClient(ip="localhost", port=5002)

        # Start the WebSocket server using the imported function
        # It needs the DiscoverPeers instance to access local_files
        self.web_socket_thread = threading.Thread(
            target=run_websocket_server,
            args=(self, "localhost", self.web_socket_port), # Pass self (P2PNode instance)
            daemon=True
        )
        self.web_socket_thread.start()
        logger.info(f"WebSocket server thread started, listening on ws://localhost:{self.web_socket_port}")

        # Start peer discovery
        self.peer_discovery.start_discovery()

        # FileServer (if used for non-WebSocket transfers)
        self.file_server_thread = threading.Thread(target=self.file_server.start_server, daemon=True)
        self.file_server_thread.start()

        logger.info("P2P Node initialized")

    def receive_file_from_peer(self, requested_filename: str):
        """
        Attempts to receive the specified file from a peer on the network.
        This method is likely triggered by an external command (e.g., from a CLI or another part of the app),
        not directly from the WebSocket message 'receive_file:filename' if that's meant for the WS to serve files.
        If 'receive_file:filename' on WS means THIS node should download, then this logic is fine.
        """
        logger.info(f"Attempting to download file from network: {requested_filename}")

        # Use find_file_source to broadcast and find a peer
        # (IP, Port, file_hash)
        source_info = self.peer_discovery.find_file_source(requested_filename)

        if source_info and source_info[0] and source_info[1] and source_info[2]:
            peer_ip, peer_port, file_hash_on_peer = source_info
            logger.info(f"File source found: {requested_filename} (hash: {file_hash_on_peer}) on peer: {peer_ip}:{peer_port}")

            download_directory = "publicFiles"
            if not os.path.exists(download_directory):
                try:
                    os.makedirs(download_directory)
                    logger.info(f"Created directory: {download_directory}")
                except OSError as e:
                    logger.error(f"Could not create directory {download_directory}: {e}")
                    return

            destination_path = os.path.join(download_directory, requested_filename)
            logger.info(f"Requesting file {requested_filename} (hash: {file_hash_on_peer}) from {peer_ip}:{peer_port} to {destination_path}")

            try:
                # Call DiscoverPeers' receive_file method
                # Signature: receive_file(self, peer_ip: str, peer_port: int, file_hash: str, destination_path: str)
                success = self.peer_discovery.receive_file(peer_ip, peer_port, file_hash_on_peer, destination_path)
                print(success)
                if success:
                    logger.info(f"'{requested_filename}' received successfully and saved to '{destination_path}'.")
                    # Optionally, add the new file to this node's shared files
                    # new_file_hash = self.hash_file(destination_path)
                    # self.files[new_file_hash] = destination_path
                    # self.peer_discovery.local_files[new_file_hash] = destination_path # Also update DiscoverPeers's copy
                    # logger.info(f"'{requested_filename}' added to local shared files.")
                else:
                    logger.warning(f"Failed to receive '{requested_filename}' from {peer_ip}:{peer_port}.")
            except Exception as e:
                logger.error(f"Error during file reception for '{requested_filename}' from {peer_ip}:{peer_port}: {e}", exc_info=True)
        else:
            logger.warning(f"File '{requested_filename}' not found on the network via broadcast.")

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
