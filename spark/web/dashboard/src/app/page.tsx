'use client';

import { useEffect, useState } from 'react';
import CommandCenter from '@/components/CommandCenter';
import AgentHealth from '@/components/AgentHealth';
import AwarenessFeed from '@/components/AwarenessFeed';
import DecisionLog from '@/components/DecisionLog';
import MemoryExplorer from '@/components/MemoryExplorer';
import SkillManager from '@/components/SkillManager';
import WorldModel from '@/components/WorldModel';

interface SparkData {
  current_goal: any;
  working_memory: any;
  agent_health: any[];
  awareness_feed: any[];
  decision_log: any[];
  memory_stats: any;
  world_model: any;
  context: any;
  skills: any[];
  system_health: any;
}

export default function Dashboard() {
  const [data, setData] = useState<SparkData | null>(null);
  const [activeTab, setActiveTab] = useState('command');

  useEffect(() => {
    const fetchStatus = async () => {
      try {
        const res = await fetch('/api/status');
        const json = await res.json();
        setData(json);
      } catch (e) {
        console.error('Failed to fetch status:', e);
      }
    };
    fetchStatus();
    const interval = setInterval(fetchStatus, 3000);
    return () => clearInterval(interval);
  }, []);

  const tabs = [
    { id: 'command', label: 'Command Center' },
    { id: 'agents', label: 'Agents' },
    { id: 'awareness', label: 'Awareness' },
    { id: 'decisions', label: 'Decisions' },
    { id: 'memory', label: 'Memory' },
    { id: 'skills', label: 'Skills' },
    { id: 'world', label: 'World Model' },
  ];

  return (
    <div className="min-h-screen p-4">
      <header className="mb-6 flex items-center justify-between">
        <h1 className="text-2xl font-bold spark-accent">S.P.A.R.K. — AI Operating System</h1>
        <div className="flex items-center gap-2">
          <span className={`status-dot ${data?.system_health?.status === 'healthy' ? 'status-active' : 'status-error'}`} />
          <span className="text-sm">{data?.system_health?.status || 'connecting...'}</span>
        </div>
      </header>

      <nav className="flex gap-2 mb-6 overflow-x-auto">
        {tabs.map(tab => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`px-4 py-2 rounded text-sm whitespace-nowrap ${
              activeTab === tab.id ? 'bg-cyan-900 text-cyan-300' : 'spark-card hover:bg-gray-800'
            }`}
          >
            {tab.label}
          </button>
        ))}
      </nav>

      <main>
        {activeTab === 'command' && <CommandCenter data={data} />}
        {activeTab === 'agents' && <AgentHealth agents={data?.agent_health || []} />}
        {activeTab === 'awareness' && <AwarenessFeed events={data?.awareness_feed || []} />}
        {activeTab === 'decisions' && <DecisionLog decisions={data?.decision_log || []} />}
        {activeTab === 'memory' && <MemoryExplorer stats={data?.memory_stats} working={data?.working_memory} />}
        {activeTab === 'skills' && <SkillManager skills={data?.skills || []} />}
        {activeTab === 'world' && <WorldModel model={data?.world_model} context={data?.context} />}
      </main>
    </div>
  );
}
