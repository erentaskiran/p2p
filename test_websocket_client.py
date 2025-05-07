#!/usr/bin/env python
import asyncio
import websockets
import sys

async def test_connection():
    """WebSocket sunucusuna bağlanıp test mesajları gönderen fonksiyon"""
    uri = "ws://localhost:8765"
    
    print(f"WebSocket sunucusuna bağlanılıyor: {uri}")
    try:
        async with websockets.connect(uri) as websocket:
            print("Bağlantı başarılı!")
            
            # Normal mesaj testi
            test_message = "Merhaba P2P Node!"
            print(f"Gönderiliyor: {test_message}")
            await websocket.send(test_message)
            response = await websocket.recv()
            print(f"Alındı: {response}")
            
            # Dosya gönderme komutu testi
            file_send_command = "send_file:test.txt"
            print(f"Gönderiliyor: {file_send_command}")
            await websocket.send(file_send_command)
            response = await websocket.recv()
            print(f"Alındı: {response}")
            
            # Dosya alma komutu testi
            file_receive_command = "receive_file:test.txt"
            print(f"Gönderiliyor: {file_receive_command}")
            await websocket.send(file_receive_command)
            response = await websocket.recv()
            print(f"Alındı: {response}")
            
    except websockets.exceptions.ConnectionClosedError:
        print("Bağlantı reddedildi! P2P Node çalışıyor mu?")
    except Exception as e:
        print(f"Bir hata oluştu: {e}")

if __name__ == "__main__":
    print("WebSocket test istemcisi başlatılıyor...")
    asyncio.run(test_connection())
    print("Test tamamlandı.")