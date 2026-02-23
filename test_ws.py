import asyncio
import websockets
import json

async def receive():
    uri = "ws://127.0.0.1:8000/ws/system"
    async with websockets.connect(uri) as websocket:
        print("Connected to system topic")
        for i in range(3):
            message = await websocket.recv()
            data = json.loads(message)
            if data.get("type") == "STATE_UPDATE":
                print(json.dumps(data.get("state", {}).get("metrics", {}), indent=2))

asyncio.run(receive())
