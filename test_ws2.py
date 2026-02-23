import websocket
import json

def on_message(ws, message):
    data = json.loads(message)
    if data.get("type") == "STATE_UPDATE":
        print(json.dumps(data.get("state", {}).get("metrics", {}), indent=2))
        ws.close()

def on_open(ws):
    print("Connected")

ws = websocket.WebSocketApp("ws://127.0.0.1:8000/ws/system",
                              on_open=on_open,
                              on_message=on_message)
ws.run_forever()
