import asyncio
import websockets
import sys
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def send_request(uri, message):
    logger.info(f"Attempting to connect to WebSocket server at {uri}")
    async with websockets.connect(uri) as websocket:
        logger.info(f"Connected to {uri}. Sending message: {message}")
        await websocket.send(message)
        logger.info(f"> Sent to {uri}: {message}")
        try:
            # Sunucudan birden fazla yanıt veya bir onay bekleyebilirsiniz.
            # Bu örnekte, ilk yankıyı (echo) alıyoruz.
            # Gerçek indirme işlemi arka planda P2PNode tarafından tetiklenir.
            response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
            logger.info(f"< Received from {uri}: {response}")
        except asyncio.TimeoutError:
            logger.warning(f"< No response received from {uri} within timeout.")
        except websockets.exceptions.ConnectionClosed as e:
            logger.error(f"< Connection closed by {uri}: {e}")
        except Exception as e:
            logger.error(f"< An error occurred during WebSocket communication with {uri}: {e}", exc_info=True)


if __name__ == "__main__":
    # Peer 2'nin (İndiren Düğüm) WebSocket URI'si
    # Yukarıdaki örnekte Peer 2'yi web_socket_port=8766 ile başlattık.
    downloader_node_websocket_uri = "ws://localhost:8765" 
    
    # Peer 1'in paylaştığı ve Peer 2'nin indirmesini istediğimiz dosyanın adı.
    # Bu dosyanın Peer 1'in "publicFiles" klasöründe olduğundan emin olun.
    file_to_request = "c.txt" 
    # Eğer publicFiles/asd/asd.txt dosyasını istiyorsanız:
    # file_to_request = "asd.txt" 

    message_to_send = f"receive_file:{file_to_request}"
    
    logger.info(f"Attempting to send command to {downloader_node_websocket_uri} to download '{file_to_request}' from another peer.")
    
    try:
        asyncio.run(send_request(downloader_node_websocket_uri, message_to_send))
    except ConnectionRefusedError:
        logger.error(f"Connection refused. Ensure the WebSocket server is running at {downloader_node_websocket_uri}")
    except Exception as e:
        logger.error(f"An unexpected error occurred in test_websocket_client: {e}", exc_info=True)

logger.info("\nTest complete. Check Node 2's console output and its 'publicFiles' directory.")