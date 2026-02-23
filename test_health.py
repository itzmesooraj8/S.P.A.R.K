import requests
import websocket

print("--- S.P.A.R.K. Health Check ---")

# Check backend API
try:
    r = requests.get("http://127.0.0.1:8000/api/projects", timeout=15)
    print(f"✅ Backend API reachable! Status: {r.status_code}")
except Exception as e:
    print(f"❌ Backend API not reachable! Error: {e}")

# Check WebSocket
try:
    ws = websocket.create_connection("ws://127.0.0.1:8000/ws/system", timeout=15)
    ws.send("ping")
    print("✅ WebSocket connected to 'system' channel!")
    ws.close()
except Exception as e:
    print(f"❌ WebSocket failed! Error: {e}")
