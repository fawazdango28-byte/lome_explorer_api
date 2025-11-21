# test_websocket.py
import asyncio
import websockets
import json

async def test_connection():
    uri = "ws://localhost:8000/ws/events/"
    async with websockets.connect(uri) as websocket:
        print("✅ Connecté!")
        
        # Recevoir le message de bienvenue
        message = await websocket.recv()
        print(f"📩 Message reçu: {message}")
        
        # Envoyer un ping
        await websocket.send(json.dumps({"type": "ping"}))
        
        # Recevoir le pong
        response = await websocket.recv()
        print(f"📩 Réponse: {response}")

asyncio.run(test_connection())