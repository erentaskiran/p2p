from __future__ import annotations
import asyncio
import websockets
import json
import os
import base64
import logging
import pathlib
import threading
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from P2PNode import P2PNode
    shared_p2p_node_instance: P2PNode | Any
else:
    shared_p2p_node_instance = None

logger = logging.getLogger(__name__)

async def handle_message(websocket, path=None):
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
                await websocket.send(json.dumps({"error": "Invalid message format, expected string."}))
                continue

            parts = message_str.split(':', 1)
            if len(parts) != 2:
                await websocket.send(json.dumps({"error": "Invalid message format. Expected 'command:payload'."}))
                continue

            command, payload = parts
            command = command.strip()
            payload = payload.strip()

            if command == "receive_file":
                requested_filename = payload
                try:
                    download_thread = threading.Thread(
                        target=shared_p2p_node_instance.receive_file_from_peer,
                        args=(requested_filename,)
                    )
                    download_thread.daemon = True
                    download_thread.start()
                    response_message = {"status": "download_initiated", "filename": requested_filename}
                    await websocket.send(json.dumps(response_message))
                except Exception as e:
                    await websocket.send(json.dumps({"error": f"Failed to initiate download for '{requested_filename}'.", "details": str(e)}))

            elif command == "get_local_files_info":
                local_files_info = []
                if hasattr(shared_p2p_node_instance, 'peer_discovery') and shared_p2p_node_instance.peer_discovery:
                    for f_hash, f_path_str in shared_p2p_node_instance.peer_discovery.local_files.items():
                        local_files_info.append({
                            "filename": os.path.basename(f_path_str),
                            "hash": f_hash,
                            "path": f_path_str
                        })
                    await websocket.send(json.dumps({"type": "local_files_list", "files": local_files_info}))
                else:
                    await websocket.send(json.dumps({"error": "Could not retrieve local files information."}))
            
            elif command == "serve_file":
                requested_filename_to_serve = payload
                found_file_path = None
                file_hash_to_send = None

                if hasattr(shared_p2p_node_instance, 'peer_discovery') and shared_p2p_node_instance.peer_discovery:
                    for f_hash, f_path_str in shared_p2p_node_instance.peer_discovery.local_files.items():
                        if os.path.basename(f_path_str) == requested_filename_to_serve:
                            found_file_path = f_path_str
                            file_hash_to_send = f_hash
                            break
                
                if found_file_path and file_hash_to_send:
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
                    except FileNotFoundError:
                        await websocket.send(json.dumps({"error": f"File '{requested_filename_to_serve}' found in manifest but not on disk."}))
                    except Exception as e:
                        await websocket.send(json.dumps({"error": f"Error processing file '{requested_filename_to_serve}'."}))
                else:
                    await websocket.send(json.dumps({"status": "file_not_found_locally", "filename": requested_filename_to_serve}))

            elif command == "discover_peers":
                if hasattr(shared_p2p_node_instance, 'peer_discovery') and shared_p2p_node_instance.peer_discovery:
                    peers = shared_p2p_node_instance.peer_discovery.peers
                    await websocket.send(json.dumps({"type": "peer_list", "peers": peers}))
                else:
                    await websocket.send(json.dumps({"error": "Could not retrieve peer list."}))
            else:
                await websocket.send(json.dumps({"error": f"Unknown command: {command}"}))

    except websockets.exceptions.ConnectionClosedOK:
        logger.info(f"Client {client_address} disconnected gracefully.")
    except websockets.exceptions.ConnectionClosedError as e:
        logger.warning(f"Client {client_address} connection closed with error: {e}")
    except Exception as e:
        logger.error(f"Error in WebSocket handler for {client_address}: {e}", exc_info=True)
        if websocket.open:
            try:
                await websocket.send(json.dumps({"error": "An unexpected server error occurred."}))
                await websocket.close(code=1011, reason="Unhandled server error")
            except websockets.exceptions.ConnectionClosed:
                pass
    finally:
        logger.info(f"Connection with {client_address} closed.")

async def start_websocket_server_main(host, port, p2p_node_instance: P2PNode | Any):
    global shared_p2p_node_instance
    shared_p2p_node_instance = p2p_node_instance
    
    if not shared_p2p_node_instance:
        logger.critical("Cannot start WebSocket server: P2PNode instance is None.")
        return

    async with websockets.serve(handle_message, host, port, max_size=None): 
        await asyncio.Future()

def run_server(p2p_node_instance: P2PNode | Any, host='localhost', port=8765):
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
    logging.basicConfig(level=logging.INFO, 
                        format='%(asctime)s - %(name)s - %(levelname)s - %(threadName)s - %(message)s')
    logger.info("Starting WebSocket server for standalone testing...")
    logger.warning("Standalone test mode for websocket.py is limited without a full P2PNode instance.")

    class MockP2PNode:
        def __init__(self):
            self.peer_discovery = self.MockDiscoverPeers()
            self.files = {}

        def receive_file_from_peer(self, filename):
            logger.info(f"[MockP2PNode] Request to download file: {filename}")

        class MockDiscoverPeers:
            def __init__(self):
                test_shared_dir = pathlib.Path(__file__).parent.parent / "publicFiles"
                test_file_path = test_shared_dir / "test.txt"
                test_shared_dir.mkdir(parents=True, exist_ok=True)
                if not test_file_path.exists():
                    try:
                        with open(test_file_path, 'w') as f:
                            f.write("This is a test file for P2P sharing.")
                    except IOError as e:
                        logger.error(f"Failed to create test file {test_file_path}: {e}")

                if test_file_path.exists():
                    example_hash = "test_file_hash_placeholder"
                    self.local_files = {example_hash: str(test_file_path)}
                else:
                    self.local_files = {}

                self.peers = ["mock_peer1:12345", "mock_peer2:54321"]

    mock_node = MockP2PNode()
    
    try:
        run_server(p2p_node_instance=mock_node, host='localhost', port=8765)
    except Exception as e:
        logger.critical(f"Failed to initialize and run standalone WebSocket server with mock: {e}", exc_info=True)
