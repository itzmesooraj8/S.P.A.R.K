import { motion } from 'framer-motion'
import { Database, FileText, Layers, Clock } from 'lucide-react'

const memoryTypes = [
  { name: 'Semantic', count: 6, icon: Database, color: 'text-spark-accent', description: 'Facts and knowledge' },
  { name: 'Episodic', count: 48, icon: FileText, color: 'text-green-500', description: 'Conversation history' },
  { name: 'Procedural', count: 3, icon: Layers, color: 'text-purple-500', description: 'Learned skills' },
  { name: 'Working', count: 1, icon: Clock, color: 'text-amber-500', description: 'Current session context' },
]

export default function MemoryPage() {
  return (
    <div className="p-6 overflow-y-auto h-full">
      <h1 className="text-xl font-mono font-medium mb-6 text-spark-text">Memory System</h1>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
        {memoryTypes.map((mem) => (
          <motion.div
            key={mem.name}
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            className="p-5 bg-[#111820] border border-spark-border rounded-xl"
          >
            <div className="flex items-center gap-3 mb-3">
              <mem.icon size={20} className={mem.color} />
              <span className="font-mono text-sm font-medium">{mem.name}</span>
              <span className="ml-auto font-mono text-lg">{mem.count}</span>
            </div>
            <p className="text-xs text-spark-muted">{mem.description}</p>
          </motion.div>
        ))}
      </div>

      {/* Recent Memory */}
      <div className="bg-[#111820] border border-spark-border rounded-xl p-5">
        <h2 className="font-mono text-sm font-medium mb-4">Recent Memory</h2>
        <div className="space-y-2">
          {['My name is Sooraj', 'I prefer VS Code', 'Working on SPARK project'].map((item, i) => (
            <div key={i} className="flex items-center justify-between p-3 bg-[#080c14] rounded-lg text-sm">
              <span className="text-spark-text">{item}</span>
              <span className="text-xs text-spark-dim font-mono">{i + 1}h ago</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
