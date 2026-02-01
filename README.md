# ⚡ S.P.A.R.K. (Sophisticated Programmable AI Research Kernel)

S.P.A.R.K. is a locally-hosted, voice-activated AI assistant powered by DeepSeek-R1 (via Ollama). It is designed to be an extensible "Iron Man" style JARVIS system that can remember facts, browse the web, control your PC, and interact via voice.

## 🚀 Features

*   **Core Reactor**: Python-based loop leveraging `deepseek-r1` for reasoning.
*   **Cortex Memory**: Long-term memory system using SQLite (`cortex.db`) to remember facts about the user.
*   **The Hands**: System automation module to execute shell commands and Python scripts.
*   **The Network**: Remote control via Telegram Bot and SSH.
*   **The Voice**: Text-to-Speech and Speech-to-Text capabilities for hands-free interaction.
*   **Real-time**: Web searching via DuckDuckGo.

## 🛠️ Installation

1.  **Prerequisites**:
    *   Python 3.10+
    *   [Ollama](https://ollama.com/) (running `deepseek-r1` or `deepseek-r1:1.5b`)
    *   FFmpeg (for voice modules)
    *   Chrome/Chromium (for Playwright browsing)

2.  **Setup**:
    ```bash
    git clone https://github.com/itzmesooraj8/S.P.A.R.K.git
    cd S.P.A.R.K
    python -m venv venv
    .\venv\Scripts\activate
    pip install -r requirements.txt
    playwright install
    ```

3.  **Environment Variables**:
    Create a `.env` file (see `.env.example`):
    ```ini
    PROJECT_ROOT=C:\path\to\SPARK
    TELEGRAM_BOT_TOKEN=your_token_here
    ALLOWED_USER_ID=your_id_here
    HOME_PC_HOST=192.168.1.x
    HOME_PC_USER=user
    ```

## ⚡ Usage

Run the core system:
```bash
.\venv\Scripts\python spark_core.py
```

*   **Voice Mode**: Press `ENTER` on the terminal to toggle the microphone.
*   **Remote**: Send messages to your Telegram Bot.

## 🛡️ License

MIT License.
