import { useEffect, useRef } from 'react';
import { useSparkStore } from '../store/sparkStore';

export function useSparkSocket() {
  const ws = useRef<WebSocket | null>(null);
  
  const setVoiceState = useSparkStore(state => state.setVoiceState);
  const setSystemMetrics = useSparkStore(state => state.setSystemMetrics);
  const setPortfolio = useSparkStore(state => state.setPortfolio);
  const setReminders = useSparkStore(state => state.setReminders);
  const addAgentLog = useSparkStore(state => state.addAgentLog);

  useEffect(() => {
    const connect = () => {
      ws.current = new WebSocket('ws://localhost:8000/ws');

      ws.current.onopen = () => {
        addAgentLog({
          timestamp: Date.now(),
          type: 'system',
          message: 'WebSocket connected to S.P.A.R.K. Core.'
        });
      };

      ws.current.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          
          if (data.type === 'voice_state') {
            setVoiceState(data.payload.state);
          } else if (data.type === 'sys_metrics') {
            setSystemMetrics(data.payload);
          } else if (data.type === 'portfolio') {
            setPortfolio(data.payload);
          } else if (data.type === 'reminders') {
            setReminders(data.payload);
          } else if (data.type === 'agent_log') {
            addAgentLog({
              timestamp: Date.now(),
              type: data.payload.type || 'info',
              message: data.payload.message
            });
          }
        } catch (err) {
          console.error("Failed to parse socket message", err);
        }
      };

      ws.current.onclose = () => {
        setTimeout(connect, 3000); // Reconnect loop
      };
    };

    connect();

    return () => {
      if (ws.current) {
        ws.current.close();
      }
    };
  }, []);

  return ws.current;
}
