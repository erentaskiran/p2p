#!/usr/bin/env python
import asyncio
import websockets
import sys

async def send_request(uri, message):
    async with websockets.connect(uri) as websocket:
        await websocket.send(message)
        print(f"> Sent to {uri}: {message}")
        try:
            # Sunucudan birden fazla yanıt veya bir onay bekleyebilirsiniz.
            # Bu örnekte, ilk yankıyı (echo) alıyoruz.
            # Gerçek indirme işlemi arka planda P2PNode tarafından tetiklenir.
            response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
            print(f"< Received from {uri}: {response}")
        except asyncio.TimeoutError:
            print(f"< No response received from {uri} within timeout.")
        except websockets.exceptions.ConnectionClosed as e:
            print(f"< Connection closed by {uri}: {e}")


if __name__ == "__main__":
    # Peer 2'nin (İndiren Düğüm) WebSocket URI'si
    # Yukarıdaki örnekte Peer 2'yi web_socket_port=8766 ile başlattık.
    downloader_node_websocket_uri = "ws://localhost:8766" 
    
    # Peer 1'in paylaştığı ve Peer 2'nin indirmesini istediğimiz dosyanın adı.
    # Bu dosyanın Peer 1'in "paylasilacak_dosyalar" klasöründe olduğundan emin olun.
    file_to_request = "test.txt" 
    # Eğer paylasilacak_dosyalar/asd/asd.txt dosyasını istiyorsanız:
    # file_to_request = "asd.txt" 

    message_to_send = f"receive_file:{file_to_request}"
    
    print(f"Attempting to send command to {downloader_node_websocket_uri} to download '{file_to_request}' from another peer.")
    
    try:
        asyncio.run(send_request(downloader_node_websocket_uri, message_to_send))
    except ConnectionRefusedError:
        print(f"Connection refused. Ensure the WebSocket server is running at {downloader_node_websocket_uri}")
    except Exception as e:
        print(f"An error occurred: {e}")

print("\nTest complete. Check Node 2's console output and its 'indirilen_dosyalar' directory.")