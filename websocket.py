import asyncio
import websockets
import json
import os
import base64
import logging
import pathlib # Added for standalone testing path
# from DiscoverPeers import DiscoverPeers # No longer directly needed here for shared instance
import threading # Added for running downloads in a separate thread
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from P2PNode import P2PNode # For type hinting, avoids circular import at runtime

logger = logging.getLogger(__name__)

# This will be set by the main application (e.g., P2PNode)
# shared_discover_peers_instance: DiscoverPeers = None # Old
shared_p2p_node_instance: 'P2PNode' | Any = None # New: P2PNode instance

async def handle_message(websocket, path):
    """
    Handles incoming WebSocket messages.
    """
    global shared_p2p_node_instance
    client_address = websocket.remote_address
    logger.info(f"Client connected from {client_address}")

    if not shared_p2p_node_instance:
        logger.error("P2PNode instance not available to WebSocket server.")
        await websocket.send(json.dumps({"error": "Server not properly configured (no P2PNode instance)."}))
        await websocket.close(code=1011, reason="Server configuration error")
        return

    try:
        async for message_str in websocket:
            logger.info(f"Received message from {client_address}: {message_str}")
            
            if not isinstance(message_str, str):
                logger.warning(f"Received non-string message from {client_address}, ignoring.")
                await websocket.send(json.dumps({"error": "Invalid message format, expected string."}))
                continue

            parts = message_str.split(':', 1)
            if len(parts) != 2:
                logger.warning(f"Invalid message format from {client_address}: {message_str}")
                await websocket.send(json.dumps({"error": "Invalid message format. Expected 'command:payload'."}))
                continue

            command, payload = parts
            command = command.strip()
            payload = payload.strip()

            if command == "receive_file":
                requested_filename = payload
                logger.info(f"WebSocket request from {client_address} to trigger download of: {requested_filename}")
                
                try:
                    # Run P2PNode's receive_file_from_peer in a new thread to avoid blocking asyncio loop
                    download_thread = threading.Thread(
                        target=shared_p2p_node_instance.receive_file_from_peer,
                        args=(requested_filename,)
                    )
                    download_thread.daemon = True # Ensure thread doesn't prevent exit
                    download_thread.start()
                    
                    response_message = {"status": "download_initiated", "filename": requested_filename}
                    await websocket.send(json.dumps(response_message))
                    logger.info(f"Download process for '{requested_filename}' initiated in a new thread for {client_address}.")
                
                except Exception as e:
                    logger.error(f"Error initiating download for '{requested_filename}' via WebSocket command: {e}", exc_info=True)
                    await websocket.send(json.dumps({"error": f"Failed to initiate download for '{requested_filename}'.", "details": str(e)}))

            elif command == "get_local_files_info": # New command to list files this node serves via WS (original receive_file behavior)
                logger.info(f"WebSocket request from {client_address} for get_local_files_info")
                # This uses the P2PNode's peer_discovery component which holds local_files
                local_files_info = []
                if hasattr(shared_p2p_node_instance, 'peer_discovery') and shared_p2p_node_instance.peer_discovery:
                    for f_hash, f_path_str in shared_p2p_node_instance.peer_discovery.local_files.items():
                        local_files_info.append({
                            "filename": os.path.basename(f_path_str),
                            "hash": f_hash,
                            "path": f_path_str # Be cautious about exposing full paths
                        })
                    await websocket.send(json.dumps({"type": "local_files_list", "files": local_files_info}))
                else:
                    await websocket.send(json.dumps({"error": "Could not retrieve local files information."}))
            
            elif command == "serve_file": # New command for a WS client to request a file directly from this node's local_files
                requested_filename_to_serve = payload
                logger.info(f"WebSocket request from {client_address} to serve_file: {requested_filename_to_serve}")
                found_file_path = None
                file_hash_to_send = None

                if hasattr(shared_p2p_node_instance, 'peer_discovery') and shared_p2p_node_instance.peer_discovery:
                    for f_hash, f_path_str in shared_p2p_node_instance.peer_discovery.local_files.items():
                        if os.path.basename(f_path_str) == requested_filename_to_serve:
                            found_file_path = f_path_str
                            file_hash_to_send = f_hash
                            break
                
                if found_file_path and file_hash_to_send:
                    logger.info(f"File '{requested_filename_to_serve}' found locally at '{found_file_path}' with hash {file_hash_to_send} for {client_address}.")
                    try:
                        with open(found_file_path, 'rb') as f:
                            file_data_bytes = f.read()
                        
                        file_data_encoded = base64.b64encode(file_data_bytes).decode('utf-8')
                        file_name_to_send = os.path.basename(found_file_path)
                        file_format = file_name_to_send.split('.')[-1] if '.' in file_name_to_send else ""

                        response_message = {
                            'type': 'file_data',
                            'file_hash': file_hash_to_send,
                            'file_name': file_name_to_send,
                            'file_format': file_format,
                            'data': file_data_encoded
                        }
                        await websocket.send(json.dumps(response_message))
                        logger.info(f"Sent file data for '{file_name_to_send}' to {client_address} over WebSocket.")
                    except FileNotFoundError:
                        logger.error(f"File not found error for: {found_file_path} (requested by {client_address})")
                        await websocket.send(json.dumps({"error": f"File '{requested_filename_to_serve}' found in manifest but not on disk."}))
                    except Exception as e:
                        logger.error(f"Error reading or sending file {found_file_path} to {client_address}: {e}", exc_info=True)
                        await websocket.send(json.dumps({"error": f"Error processing file '{requested_filename_to_serve}'."}))
                else:
                    logger.warning(f"File '{requested_filename_to_serve}' not found in local_files for WebSocket request from {client_address}.")
                    await websocket.send(json.dumps({"status": "file_not_found_locally", "filename": requested_filename_to_serve}))

            elif command == "discover_peers":
                if hasattr(shared_p2p_node_instance, 'peer_discovery') and shared_p2p_node_instance.peer_discovery:
                    peers = shared_p2p_node_instance.peer_discovery.peers
                    await websocket.send(json.dumps({"type": "peer_list", "peers": peers}))
                    logger.info(f"Sent peer list to {client_address}: {peers}")
                else:
                    await websocket.send(json.dumps({"error": "Could not retrieve peer list."}))
                    logger.warning(f"Peer discovery component not available for discover_peers command from {client_address}")
            else:
                logger.warning(f"Unknown command '{command}' from {client_address}")
                await websocket.send(json.dumps({"error": f"Unknown command: {command}"}))

    except websockets.exceptions.ConnectionClosedOK:
        logger.info(f"Client {client_address} disconnected gracefully.")
    except websockets.exceptions.ConnectionClosedError as e:
        logger.warning(f"Client {client_address} connection closed with error: {e}")
    except Exception as e:
        logger.error(f"Error in WebSocket handler for {client_address}: {e}", exc_info=True)
        if websocket.open:
            try:
                # Send a generic error and close with 1011 if an unhandled exception occurs
                await websocket.send(json.dumps({"error": "An unexpected server error occurred."}))
                await websocket.close(code=1011, reason="Unhandled server error")
            except websockets.exceptions.ConnectionClosed:
                pass # Client already gone
    finally:
        logger.info(f"Connection with {client_address} closed.")


async def start_websocket_server_main(host, port, p2p_node_instance: 'P2PNode' | Any):
    """
    Starts the WebSocket server and keeps it running.
    Now accepts a P2PNode instance.
    """
    global shared_p2p_node_instance
    shared_p2p_node_instance = p2p_node_instance
    
    if not shared_p2p_node_instance:
        logger.critical("Cannot start WebSocket server: P2PNode instance is None.")
        return

    logger.info(f"Attempting to start WebSocket server on {host}:{port}...")
    async with websockets.serve(handle_message, host, port, max_size=None): 
        logger.info(f"WebSocket server started on ws://{host}:{port}")
        await asyncio.Future()  # Run forever

def run_server(p2p_node_instance: 'P2PNode' | Any, host='localhost', port=8765):
    """
    Utility function to run the WebSocket server.
    Accepts a P2PNode instance.
    """
    try:
        asyncio.run(start_websocket_server_main(host, port, p2p_node_instance))
    except KeyboardInterrupt:
        logger.info("WebSocket server shutting down due to KeyboardInterrupt...")
    except OSError as e:
        logger.error(f"Failed to start WebSocket server on {host}:{port}. Error: {e}")
        if "Address already in use" in str(e):
            logger.error("The port is likely already in use by another application or an old instance of this server.")
        raise
    except Exception as e:
        logger.critical(f"An unexpected error occurred while trying to run the WebSocket server: {e}", exc_info=True)
        raise


if __name__ == '__main__':
    # This standalone test block needs a P2PNode instance to run correctly with the new design.
    # For simplicity, we'll just log that it's a test and would require P2PNode.
    logging.basicConfig(level=logging.INFO, 
                        format='%(asctime)s - %(name)s - %(levelname)s - %(threadName)s - %(message)s')
    logger.info("Starting WebSocket server for standalone testing...")
    logger.warning("Standalone test mode for websocket.py is limited without a full P2PNode instance.")
    logger.warning("To test fully, integrate with P2PNode.py or create a mock P2PNode here.")

    # Example of how it might be mocked (very basic):
    class MockP2PNode:
        def __init__(self):
            self.peer_discovery = self.MockDiscoverPeers()
            self.files = {} # Mock files
            logger.info("MockP2PNode initialized for standalone WebSocket test.")

        def receive_file_from_peer(self, filename):
            logger.info(f"[MockP2PNode] Request to download file: {filename}")
            # Simulate download initiation
            logger.info(f"[MockP2PNode] Simulated download for {filename} initiated.")
            # In a real scenario, this would interact with the network.

        class MockDiscoverPeers:
            def __init__(self):
                self.local_files = {"hash_of_test.txt": "paylasilacak_dosyalar/test.txt"}
                self.peers = ["mock_peer1:12345", "mock_peer2:54321"]
                logger.info("MockDiscoverPeers initialized for standalone WebSocket test.")
                # Ensure dummy file exists for serve_file testing
                test_shared_dir = pathlib.Path(__file__).parent / "paylasilacak_dosyalar"
                test_file_path = test_shared_dir / "test.txt"
                if not test_shared_dir.exists(): test_shared_dir.mkdir(parents=True, exist_ok=True)
                if not test_file_path.exists():
                    with open(test_file_path, "w") as f: f.write("Test content for standalone WS.")
                    logger.info(f"Created dummy file: {test_file_path}")


    mock_node = MockP2PNode()
    
    try:
        # Pass the mock P2PNode instance
        run_server(p2p_node_instance=mock_node, host='localhost', port=8765)
    except Exception as e:
        logger.critical(f"Failed to initialize and run standalone WebSocket server with mock: {e}", exc_info=True)
