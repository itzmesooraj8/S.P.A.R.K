/* S.P.A.R.K. — JARVIS Dashboard JavaScript */

const API_BASE = 'http://localhost:8080';
const WS_URL = 'ws://localhost:8080/ws';

class SparkDashboard {
    constructor() {
        this.ws = null;
        this.isConnected = false;
        this.messages = [];
        this.isThinking = false;
        this.init();
    }

    init() {
        this.bindEvents();
        this.connectWebSocket();
        this.addWelcomeMessage();
    }

    bindEvents() {
        const input = document.getElementById('chat-input');
        const sendBtn = document.getElementById('send-btn');
        const micBtn = document.getElementById('mic-btn');

        input.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                this.sendMessage();
            }
        });

        sendBtn.addEventListener('click', () => this.sendMessage());

        micBtn.addEventListener('click', () => this.toggleVoice());

        document.querySelectorAll('.cmd-pill').forEach(btn => {
            btn.addEventListener('click', () => {
                const cmd = btn.dataset.cmd;
                if (cmd.endsWith('...')) {
                    input.value = cmd.slice(0, -3);
                    input.focus();
                } else {
                    input.value = cmd;
                    this.sendMessage();
                }
            });
        });

        document.querySelectorAll('.nav-item').forEach(btn => {
            btn.addEventListener('click', () => {
                document.querySelectorAll('.nav-item').forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
            });
        });
    }

    connectWebSocket() {
        try {
            this.ws = new WebSocket(WS_URL);
            this.ws.onopen = () => {
                this.isConnected = true;
                this.updateConnectionStatus(true);
                console.log('Connected to SPARK');
            };
            this.ws.onmessage = (event) => {
                const data = JSON.parse(event.data);
                this.handleWSMessage(data);
            };
            this.ws.onclose = () => {
                this.isConnected = false;
                this.updateConnectionStatus(false);
                setTimeout(() => this.connectWebSocket(), 3000);
            };
            this.ws.onerror = (error) => {
                console.error('WebSocket error:', error);
            };
        } catch (e) {
            console.error('WebSocket connection failed:', e);
            setTimeout(() => this.connectWebSocket(), 3000);
        }
    }

    handleWSMessage(data) {
        if (data.working_memory) {
            this.updateStats(data);
        }
    }

    updateConnectionStatus(connected) {
        const groqStatus = document.getElementById('groq-status');
        const dot = groqStatus.querySelector('.chip-dot');
        const label = groqStatus.querySelector('.chip-label');
        if (connected) {
            dot.className = 'chip-dot green';
            label.textContent = 'Groq Live';
        } else {
            dot.className = 'chip-dot red';
            label.textContent = 'Disconnected';
        }
    }

    updateStats(data) {
        if (data.system_health) {
            const cpu = data.system_health.cpu_percent || 0;
            const mem = data.system_health.memory_percent || 0;
        }
    }

    addWelcomeMessage() {
        this.addMessage('spark', 'Good afternoon, Sooraj. All systems nominal.', 'conversation');
    }

    async sendMessage() {
        const input = document.getElementById('chat-input');
        const text = input.value.trim();
        if (!text || this.isThinking) return;

        this.addMessage('user', text);
        input.value = '';
        this.showThinking();

        try {
            const response = await fetch(`${API_BASE}/api/command`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ input: text }),
            });

            const data = await response.json();
            this.hideThinking();

            const reply = data.reply || 'No response received.';
            const action = data.action || 'conversation';
            this.addMessage('spark', reply, action);
        } catch (error) {
            this.hideThinking();
            this.addMessage('spark', `Connection error: ${error.message}`, 'error');
        }
    }

    addMessage(role, content, intent = 'conversation') {
        const container = document.getElementById('chat-messages');
        const msg = document.createElement('div');
        msg.className = `message ${role}`;

        const now = new Date();
        const timeStr = now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

        let intentTag = '';
        if (role === 'spark' && intent !== 'conversation') {
            intentTag = `<span class="intent-tag">${intent}</span>`;
        }

        msg.innerHTML = `
            <div class="message-header">
                <span>${role === 'spark' ? 'S.P.A.R.K' : 'Sooraj'}</span>
                <span>${timeStr}</span>
                ${intentTag}
            </div>
            <div class="message-bubble">${this.formatContent(content)}</div>
        `;

        container.appendChild(msg);
        container.scrollTop = container.scrollHeight;
    }

    formatContent(text) {
        return text
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/\n/g, '<br>')
            .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
    }

    showThinking() {
        this.isThinking = true;
        const container = document.getElementById('chat-messages');
        const thinking = document.createElement('div');
        thinking.className = 'message spark';
        thinking.id = 'thinking-indicator';
        thinking.innerHTML = `
            <div class="message-header">
                <span>S.P.A.R.K</span>
                <span>thinking...</span>
            </div>
            <div class="thinking-indicator">
                <div class="wave-bar"></div>
                <div class="wave-bar"></div>
                <div class="wave-bar"></div>
                <div class="wave-bar"></div>
                <div class="wave-bar"></div>
            </div>
        `;
        container.appendChild(thinking);
        container.scrollTop = container.scrollHeight;
    }

    hideThinking() {
        this.isThinking = false;
        const thinking = document.getElementById('thinking-indicator');
        if (thinking) thinking.remove();
    }

    toggleVoice() {
        const micBtn = document.getElementById('mic-btn');
        const overlay = document.getElementById('voice-overlay');

        if (micBtn.classList.contains('active')) {
            micBtn.classList.remove('active');
            overlay.classList.remove('active');
        } else {
            micBtn.classList.add('active');
            overlay.classList.add('active');
        }
    }
}

document.addEventListener('DOMContentLoaded', () => {
    new SparkDashboard();
});
