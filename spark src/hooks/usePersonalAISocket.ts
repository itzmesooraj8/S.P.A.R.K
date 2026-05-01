import { useState, useEffect, useCallback, useRef } from 'react';
import { toast } from '@/hooks/use-toast';

export interface ChatMessage {
  id: string;
  sender: 'ai' | 'user';
  text: string;
}

export function usePersonalAISocket() {
  const [messages, setMessages] = useState<ChatMessage[]>([{
    id: 'init',
    sender: 'ai',
    text: 'SPARK Personal AI initialized. Ready for your command.'
  }]);
  const [isConnected, setIsConnected] = useState(false);
  const [activityLogs, setActivityLogs] = useState<string[]>(['[SYSTEM] SPARK Boot sequence initiated.']);
  const wsRef = useRef<WebSocket | null>(null);

  const logActivity = useCallback((msg: string) => {
    const time = new Date().toLocaleTimeString();
    setActivityLogs(prev => [...prev, `[${time}] ${msg}`]);
  }, []);

  const appendMessage = useCallback((sender: 'ai' | 'user', text: string) => {
    setMessages(prev => [...prev, { id: Math.random().toString(36).substring(7), sender, text }]);
    logActivity(`${sender.toUpperCase()} message added.`);
  }, [logActivity]);

  useEffect(() => {
    const connect = () => {
      const ws = new WebSocket('ws://127.0.0.1:8000/ws/personal/chat');

      ws.onopen = () => {
        setIsConnected(true);
        logActivity('WebSocket Connected (Duplex Stream Ready)');
      };

      ws.onclose = () => {
        setIsConnected(false);
        logActivity('WebSocket Disconnected. Reconnecting...');
        setTimeout(connect, 3000);
      };

      ws.onmessage = (e) => {
        appendMessage('ai', e.data);
      };

      wsRef.current = ws;
    };

    connect();

    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, [appendMessage, logActivity]);

  const sendToBrain = async (message: string) => {
    if (!message.trim()) return;

    appendMessage('user', message);

    if (message.toLowerCase().startsWith('search ')) {
      const query = message.substring(7);
      logActivity(`Routing to web search: ${query}`);
      window.open(`https://google.com/search?q=${encodeURIComponent(query)}`);
      appendMessage('ai', 'Opening search results for you.');
      return;
    }

    logActivity('Sending request to SPARK Core...');
    try {
      const res = await fetch('http://127.0.0.1:8000/api/personal/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: message, requires_online: true })
      });
      const data = await res.json();
      appendMessage('ai', `<b>[${data.source}]</b><br/>${data.response}`);
    } catch (err: any) {
      logActivity('API Error: ' + err.message);
      
      if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
        logActivity('Falling back to WebSocket tunnel...');
        wsRef.current.send(message);
      } else {
        appendMessage('ai', '[System Status] Backend offline. Please start SPARK Core.');
      }
    }
  };

  return {
    messages,
    isConnected,
    activityLogs,
    sendToBrain,
    logActivity,
  };
}
