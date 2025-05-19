import logging
from utils.DiscoverPeers import DiscoverPeers
import threading
from utils.FileManager import FileServer, FileClient
import os
from utils.websocket import run_server as run_websocket_server

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class P2PNode:
    def __init__(self, port: int = 5003, web_socket_port: int = 8765):
        self.port = port
        self.web_socket_port = web_socket_port
        logger.info(f"Initializing P2PNode on port {port} with WebSocket port {web_socket_port}")

        self.peers = []
        self.files = {}
        logger.info(f"Indexed files: {self.files}")

        self.peer_discovery = DiscoverPeers(self.port)
        self.file_server = FileServer(host="localhost", port=5001) 
        self.file_client = FileClient(ip="localhost", port=5002)

        self.web_socket_thread = threading.Thread(
            target=run_websocket_server,
            args=(self, "localhost", self.web_socket_port),
            daemon=True
        )
        self.web_socket_thread.start()
        logger.info(f"WebSocket server thread started, listening on ws://localhost:{self.web_socket_port}")

        self.peer_discovery.start_discovery()

        self.file_server_thread = threading.Thread(target=self.file_server.start_server, daemon=True)
        self.file_server_thread.start()

        logger.info("P2P Node initialized")

    def receive_file_from_peer(self, requested_filename: str):
        logger.info(f"Attempting to download file from network: {requested_filename}")

        source_info = self.peer_discovery.find_file_source(requested_filename)

        if source_info and source_info[0] and source_info[1] and source_info[2]:
            peer_ip, peer_port, file_hash_on_peer = source_info
            logger.info(f"File source found: {requested_filename} (hash: {file_hash_on_peer}) on peer: {peer_ip}:{peer_port}")

            download_directory = "publicFiles"
            if not os.path.exists(download_directory):
                try:
                    logger.info(f"Created directory: {download_directory}")
                except OSError as e:
                    logger.error(f"Could not create directory {download_directory}: {e}")
                    return

            destination_path = os.path.join(download_directory, requested_filename)
            logger.info(f"Requesting file {requested_filename} (hash: {file_hash_on_peer}) from {peer_ip}:{peer_port} to {destination_path}")

            try:
                success = self.peer_discovery.receive_file(peer_ip, peer_port, file_hash_on_peer, destination_path)
                print(success)
                if success:
                    logger.info(f"'{requested_filename}' received successfully and saved to '{destination_path}'.")
                else:
                    logger.warning(f"Failed to receive '{requested_filename}' from {peer_ip}:{peer_port}.")
            except Exception as e:
                logger.error(f"Error during file reception for '{requested_filename}' from {peer_ip}:{peer_port}: {e}", exc_info=True)
        else:
            logger.warning(f"File '{requested_filename}' not found on the network via broadcast.")
