import { create } from 'zustand';

export type VoiceState = 'idle' | 'listening' | 'processing' | 'speaking';

export interface SystemMetrics {
  cpu: number;
  ramFree: number;
  ramTotal: number;
  diskFree: number;
  diskTotal: number;
  batteryPercent: number;
}

export interface PortfolioPosition {
  symbol: string;
  qty: number;
  buyPrice: number;
  currentPrice: number;
  pnl: number;
  pnlPercent: number;
}

export interface AgentLogEntry {
  id: string;
  timestamp: number;
  type: 'voice' | 'web' | 'system' | 'error' | 'info';
  message: string;
}

export interface Reminder {
  id: string;
  time: string;
  message: string;
  active: boolean;
}

interface SparkStore {
  voiceState: VoiceState;
  systemMetrics: SystemMetrics | null;
  portfolio: PortfolioPosition[];
  reminders: Reminder[];
  agentLog: AgentLogEntry[];
  activeTheme: 'cyan' | 'red' | 'white' | 'amber';
  
  setVoiceState: (state: VoiceState) => void;
  setSystemMetrics: (metrics: SystemMetrics) => void;
  setPortfolio: (portfolio: PortfolioPosition[]) => void;
  setReminders: (reminders: Reminder[]) => void;
  addAgentLog: (entry: Omit<AgentLogEntry, 'id'>) => void;
  setTheme: (theme: 'cyan' | 'red' | 'white' | 'amber') => void;
}

export const useSparkStore = create<SparkStore>((set) => ({
  voiceState: 'idle',
  systemMetrics: null,
  portfolio: [],
  reminders: [],
  agentLog: [],
  activeTheme: 'cyan',

  setVoiceState: (state) => set({ voiceState: state }),
  setSystemMetrics: (metrics) => set({ systemMetrics: metrics }),
  setPortfolio: (portfolio) => set({ portfolio }),
  setReminders: (reminders) => set({ reminders }),
  addAgentLog: (entry) => set((state) => ({
    agentLog: [...state.agentLog, { ...entry, id: Date.now().toString() + Math.random() }].slice(-100)
  })),
  setTheme: (theme) => set({ activeTheme: theme }),
}));
