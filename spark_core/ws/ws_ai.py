import json
import httpx
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

ws_ai_router = APIRouter()

@ws_ai_router.websocket("/ws/ai")
async def ai_websocket_handler(websocket: WebSocket):
    await websocket.accept()
    
    try:
        while True:
            raw_data = await websocket.receive_text()
            try:
                msg = json.loads(raw_data)
                user_text = msg.get("message", "")
                
                if not user_text:
                    continue

                payload = {
                    "model": "gemma3:4b",
                    "messages": [{"role": "user", "content": user_text}],
                    "stream": True
                }

                try:
                    async with httpx.AsyncClient(timeout=120.0) as client:
                        async with client.stream("POST", "http://127.0.0.1:11434/api/chat", json=payload) as response:
                            if response.status_code == 200:
                                async for line in response.aiter_lines():
                                    if line:
                                        try:
                                            chunk = json.loads(line)
                                            token = chunk.get("message", {}).get("content", "")
                                            if token:
                                                # Feed frontend direct token string
                                                await websocket.send_json({
                                                    "type": "response_token",
                                                    "token": token
                                                })
                                        except json.JSONDecodeError:
                                            pass
                            else:
                                await websocket.send_json({
                                    "type": "response_token", 
                                    "token": "[SPARK: Ollama error — is it running?]"
                                })
                except Exception:
                    await websocket.send_json({
                        "type": "response_token", 
                        "token": "[SPARK: Ollama error — is it running?]"
                    })
                
                # Command sequence end, unlock input bar
                await websocket.send_json({"type": "response_done"})

            except json.JSONDecodeError:
                pass
                
    except WebSocketDisconnect:
        pass
