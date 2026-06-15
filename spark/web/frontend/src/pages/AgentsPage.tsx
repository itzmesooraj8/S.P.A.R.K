import { motion } from 'framer-motion'
import { Brain, Eye, Database, Cpu, Activity } from 'lucide-react'

const agents = [
  { name: 'Planner', status: 'idle', icon: Brain, color: 'text-spark-accent' },
  { name: 'Executor', status: 'idle', icon: Cpu, color: 'text-green-500' },
  { name: 'Memory', status: 'idle', icon: Database, color: 'text-blue-500' },
  { name: 'Reflection', status: 'idle', icon: Activity, color: 'text-purple-500' },
  { name: 'Observer', status: 'running', icon: Eye, color: 'text-amber-500' },
]

export default function AgentsPage() {
  return (
    <div className="p-6 overflow-y-auto h-full">
      <h1 className="text-xl font-mono font-medium mb-6 text-spark-text">Agent Status</h1>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {agents.map((agent) => (
          <motion.div
            key={agent.name}
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            className="p-5 bg-[#111820] border border-spark-border rounded-xl"
          >
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-3">
                <agent.icon size={20} className={agent.color} />
                <span className="font-mono text-sm font-medium">{agent.name}</span>
              </div>
              <div className="flex items-center gap-2">
                <div className={`w-2 h-2 rounded-full ${agent.status === 'running' ? 'bg-green-500 animate-pulse' : 'bg-spark-dim'}`} />
                <span className="text-xs text-spark-muted">{agent.status}</span>
              </div>
            </div>

            <div className="space-y-2 text-xs text-spark-muted">
              <div className="flex justify-between">
                <span>Last Run</span>
                <span className="font-mono">--</span>
              </div>
              <div className="flex justify-between">
                <span>Latency</span>
                <span className="font-mono">0ms</span>
              </div>
              <div className="flex justify-between">
                <span>Errors</span>
                <span className="font-mono">0</span>
              </div>
            </div>
          </motion.div>
        ))}
      </div>
    </div>
  )
}
