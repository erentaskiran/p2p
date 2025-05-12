import asyncio
import websockets
import json
import os
import base64
import logging
import pathlib # Added for standalone testing path
from DiscoverPeers import DiscoverPeers

logger = logging.getLogger(__name__)

# This will be set by the main application (e.g., P2PNode)
shared_discover_peers_instance: DiscoverPeers = None

async def handle_message(websocket, path):
    """
    Handles incoming WebSocket messages.
    """
    global shared_discover_peers_instance
    client_address = websocket.remote_address
    logger.info(f"Client connected from {client_address}")

    if not shared_discover_peers_instance:
        logger.error("DiscoverPeers instance not available to WebSocket server.")
        await websocket.send(json.dumps({"error": "Server not properly configured (no DiscoverPeers instance)."}))
        await websocket.close()
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
                logger.info(f"WebSocket request from {client_address} for receive_file: {requested_filename}")

                found_file_path = None
                file_hash_to_send = None

                # Access local_files from the shared DiscoverPeers instance
                for f_hash, f_path_str in shared_discover_peers_instance.local_files.items():
                    if os.path.basename(f_path_str) == requested_filename:
                        found_file_path = f_path_str
                        file_hash_to_send = f_hash
                        break
                
                if found_file_path and file_hash_to_send:
                    logger.info(f"File '{requested_filename}' found locally at '{found_file_path}' with hash {file_hash_to_send} for {client_address}.")
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
                        await websocket.send(json.dumps({"error": f"File '{requested_filename}' found in manifest but not on disk."}))
                    except Exception as e:
                        logger.error(f"Error reading or sending file {found_file_path} to {client_address}: {e}", exc_info=True)
                        await websocket.send(json.dumps({"error": f"Error processing file '{requested_filename}'."}))
                else:
                    logger.warning(f"File '{requested_filename}' not found in local_files for WebSocket request from {client_address}.")
                    await websocket.send(json.dumps({"status": "file_not_found_locally", "filename": requested_filename}))
            
            elif command == "discover_peers": # Example of another command
                peers = shared_discover_peers_instance.peers
                await websocket.send(json.dumps({"type": "peer_list", "peers": peers}))
                logger.info(f"Sent peer list to {client_address}: {peers}")

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
                await websocket.send(json.dumps({"error": "An unexpected server error occurred."}))
            except websockets.exceptions.ConnectionClosed:
                pass # Client already gone
    finally:
        logger.info(f"Connection with {client_address} closed.")


async def start_websocket_server_main(host, port, discover_peers_instance: DiscoverPeers):
    """
    Starts the WebSocket server and keeps it running.
    """
    global shared_discover_peers_instance
    shared_discover_peers_instance = discover_peers_instance
    
    if not shared_discover_peers_instance:
        logger.critical("Cannot start WebSocket server: DiscoverPeers instance is None.")
        return

    logger.info(f"Attempting to start WebSocket server on {host}:{port}...")
    # Set a higher max_size if you expect to send large files
    # For example, max_size=10*1024*1024 for 10MB
    async with websockets.serve(handle_message, host, port, max_size=None): # max_size=None for unlimited, or set a specific limit
        logger.info(f"WebSocket server started on ws://{host}:{port}")
        await asyncio.Future()  # Run forever

def run_server(discover_peers_instance: DiscoverPeers, host='localhost', port=8765):
    """
    Utility function to run the WebSocket server.
    This should be called from your main application script (e.g., P2PNode.py).
    """
    try:
        asyncio.run(start_websocket_server_main(host, port, discover_peers_instance))
    except KeyboardInterrupt:
        logger.info("WebSocket server shutting down due to KeyboardInterrupt...")
    except OSError as e:
        logger.error(f"Failed to start WebSocket server on {host}:{port}. Error: {e}")
        if "Address already in use" in str(e):
            logger.error("The port is likely already in use by another application or an old instance of this server.")
        # Exit or handle as appropriate for your application
        # For now, just re-raising to make it visible
        raise
    except Exception as e:
        logger.critical(f"An unexpected error occurred while trying to run the WebSocket server: {e}", exc_info=True)
        raise


if __name__ == '__main__':
    # This is a minimal setup for standalone testing of websocket.py.
    # In a real application, DiscoverPeers would be initialized by P2PNode or main.py
    # with actual local files and manifest.
    
    # Setup basic logging for standalone test
    logging.basicConfig(level=logging.INFO, 
                        format='%(asctime)s - %(name)s - %(levelname)s - %(threadName)s - %(message)s')
    logger.info("Starting WebSocket server for standalone testing...")

    # Create a dummy DiscoverPeers instance for testing
    # Ensure 'paylasilacak_dosyalar' directory and 'test.txt' exist for this to work fully.
    current_script_dir = pathlib.Path(__file__).parent
    test_shared_dir = current_script_dir / "paylasilacak_dosyalar"
    test_file_name = "test.txt"
    test_file_path = test_shared_dir / test_file_name
    
    # Create dummy file and directory if they don't exist for testing
    if not test_shared_dir.exists():
        logger.info(f"Creating dummy shared directory: {test_shared_dir}")
        test_shared_dir.mkdir(parents=True, exist_ok=True)
    if not test_file_path.exists():
        logger.info(f"Creating dummy file for testing: {test_file_path}")
        with open(test_file_path, "w") as f:
            f.write("This is a test file for WebSocket standalone testing.")
    
    dummy_local_files = {}
    if test_file_path.exists():
        # Using a simple hash for testing (filename itself for simplicity here)
        # In a real scenario, this hash would come from your manifest/file hashing logic
        dummy_local_files = { f"hash_of_{test_file_name}": str(test_file_path) }
    else:
        logger.warning(f"Test file {test_file_path} could not be found or created for standalone test.")


    # Dummy port for DiscoverPeers, not actually used for UDP discovery in this standalone WS test
    # The local_files dictionary is the important part for the 'receive_file' command.
    try:
        dp_instance = DiscoverPeers(port=12345, local_files=dummy_local_files)
        logger.info(f"Dummy DiscoverPeers instance created with local_files: {dp_instance.local_files}")
        
        # Ensure the shared instance is set for the handler
        shared_discover_peers_instance = dp_instance 

        run_server(discover_peers_instance=dp_instance, host='localhost', port=8765)
    except Exception as e:
        logger.critical(f"Failed to initialize and run standalone WebSocket server: {e}", exc_info=True)
