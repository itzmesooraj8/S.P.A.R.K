# SPARK Core (Backend Services)

This directory contains the Python-based backend for the S.P.A.R.K. system. It serves as the central nervous system, handling incoming requests, managing WebSockets, orchestrating LLM interactions, and running secure code analysis tools.

## 🧠 Core Architecture

The backend is built with **FastAPI** and follows a modular architecture:

- **main.py**: Entry point. Sets up the FastAPI app, CORS, and routes.
- **ws/**: WebSocket connection managers for efficient real-time communication.
    - system: Pushes hardware metrics (CPU/RAM/Net) and security alerts.
    - i: Handles chat streams, tool execution feedback, and audio data.
- **llm/**: Abstraction layer for Large Language Models. Supports local Ollama instances and cloud API fallbacks.
- **	ools/**: Registry of capabilities the AI can invoke (FileSystem, WebSearch, CodeAnalysis).
- **sandbox/**: Docker management for safely executing untrusted or generated code.
- **memory/**: Vector database integrations (ChromaDB) for long-term project memory.

## 🔧 backend Configuration

Configuration is managed via config/secrets.yaml (located in the project root) and environment variables.

### Key Configuration Options

| Setting | description | Default |
|---------|-------------|---------|
| LLM_PROVIDER | AI Model Provider | ollama |
| LLM_MODEL | Specific Model Name | llama3:8b |
| SANDBOX_MODE | Code Execution Environment | docker |
| VOICE_ENABLED | Enable STT/TTS modules | 	rue |

## 📦 Dependencies

Major dependencies include:
- astapi & uvicorn: Web server and API framework.
- websockets: Real-time communication.
- docker: Python Docker SDK for container management.
- psutil: System hardware monitoring.
- langchain / chromadb: (Optional) For advanced memory features.

## 🚀 Development

### Running the Core Directly

If you need to debug the backend in isolation:

1.  Navigate to the project root.
2.  Activate your virtual environment.
3.  Run the server wrapper:

    `powershell
    python run_server.py
    `

    *Alternatively, from within spark_core/:*
    `powershell
    python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
    `

### Testing

Run the test suite to verify core functionality:

`powershell
pytest test_health.py test_ws.py
`

## 🔐 Security

The core system is designed with security in mind:
- **Sandboxing**: Heavy tooling and generated code run in ephemeral Docker containers to prevent host system modification.
- **Validation**: All WebSocket messages are validated against strict schemas.
- **Environment Isolation**: The .env and secrets.yaml files are excluded from version control.

## 📜 API Documentation

Once running, interactive documentation is available at:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
