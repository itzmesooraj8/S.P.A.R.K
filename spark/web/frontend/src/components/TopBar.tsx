import { motion } from 'framer-motion'
import { Mic, User } from 'lucide-react'

export default function TopBar() {
  return (
    <header className="h-14 bg-[#0d1117] border-b border-spark-border flex items-center justify-between px-5">
      {/* Status Chips */}
      <div className="flex items-center gap-3">
        <StatusChip label="Groq Live" status="green" />
        <StatusChip label="Memory Active" status="blue" />
        <StatusChip label="Voice Standby" status="amber" />
      </div>

      {/* User */}
      <div className="flex items-center gap-3">
        <button className="p-2 rounded-lg border border-spark-border text-spark-muted hover:text-spark-accent hover:border-spark-accent transition-colors">
          <Mic size={16} />
        </button>
        <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg border border-spark-border">
          <User size={14} className="text-spark-muted" />
          <span className="text-sm text-spark-muted">Sooraj</span>
        </div>
      </div>
    </header>
  )
}

function StatusChip({ label, status }: { label: string; status: 'green' | 'blue' | 'amber' }) {
  const colors = {
    green: 'bg-green-500',
    blue: 'bg-spark-accent',
    amber: 'bg-amber-500',
  }

  return (
    <div className="flex items-center gap-2 px-3 py-1 rounded-md border border-spark-border font-mono text-xs">
      <div className={`w-1.5 h-1.5 rounded-full ${colors[status]}`} />
      <span className="text-spark-muted">{label}</span>
    </div>
  )
}
