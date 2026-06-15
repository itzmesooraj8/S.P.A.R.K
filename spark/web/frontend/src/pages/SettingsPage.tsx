import { motion } from 'framer-motion'
import { Key, Cpu, Database, Shield, Bell } from 'lucide-react'

const settingsSections = [
  {
    title: 'API Keys',
    icon: Key,
    items: [
      { label: 'Groq API Key', status: 'configured', type: 'password' },
      { label: 'Ollama Endpoint', status: 'not configured', type: 'text' },
    ],
  },
  {
    title: 'Model',
    icon: Cpu,
    items: [
      { label: 'Primary Model', value: 'llama-3.1-8b-instant' },
      { label: 'Fallback Model', value: 'gemma2:2b' },
      { label: 'Max Tokens', value: '500' },
    ],
  },
  {
    title: 'Memory',
    icon: Database,
    items: [
      { label: 'ChromaDB Path', value: '.spark_memory' },
      { label: 'Working Memory Limit', value: '20 turns' },
    ],
  },
  {
    title: 'Security',
    icon: Shield,
    items: [
      { label: 'Policy Engine', status: 'active' },
      { label: 'Authority Layer', status: 'active' },
      { label: 'Sandbox Mode', status: 'local' },
    ],
  },
]

export default function SettingsPage() {
  return (
    <div className="p-6 overflow-y-auto h-full">
      <h1 className="text-xl font-mono font-medium mb-6 text-spark-text">Settings</h1>

      <div className="space-y-6 max-w-2xl">
        {settingsSections.map((section) => (
          <motion.div
            key={section.title}
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            className="bg-[#111820] border border-spark-border rounded-xl p-5"
          >
            <div className="flex items-center gap-3 mb-4">
              <section.icon size={18} className="text-spark-accent" />
              <h2 className="font-mono text-sm font-medium">{section.title}</h2>
            </div>

            <div className="space-y-3">
              {section.items.map((item) => (
                <div key={item.label} className="flex items-center justify-between p-3 bg-[#080c14] rounded-lg">
                  <span className="text-sm text-spark-muted">{item.label}</span>
                  {item.value && (
                    <span className="font-mono text-xs text-spark-text">{item.value}</span>
                  )}
                  {item.status && (
                    <span className={`text-xs font-mono px-2 py-0.5 rounded ${
                      item.status === 'active' || item.status === 'configured'
                        ? 'bg-green-500/10 text-green-500'
                        : 'bg-spark-dim/20 text-spark-dim'
                    }`}>
                      {item.status}
                    </span>
                  )}
                </div>
              ))}
            </div>
          </motion.div>
        ))}
      </div>
    </div>
  )
}
