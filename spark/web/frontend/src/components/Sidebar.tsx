import { NavLink } from 'react-router-dom'
import { motion } from 'framer-motion'
import { MessageSquare, Brain, Database, Newspaper, Settings, Radio } from 'lucide-react'

const navItems = [
  { to: '/chat', icon: MessageSquare, label: 'Chat' },
  { to: '/agents', icon: Brain, label: 'Agents' },
  { to: '/memory', icon: Database, label: 'Memory' },
  { to: '/news', icon: Newspaper, label: 'News' },
  { to: '/settings', icon: Settings, label: 'Settings' },
]

export default function Sidebar() {
  return (
    <aside className="w-[220px] h-screen bg-[#0d1117] border-r border-spark-border flex flex-col">
      {/* Brand */}
      <div className="p-5 flex items-center gap-3">
        <motion.div
          className="w-2.5 h-2.5 bg-spark-accent rounded-full"
          animate={{ opacity: [1, 0.5, 1], boxShadow: ['0 0 8px #63c4ff', '0 0 4px #63c4ff', '0 0 8px #63c4ff'] }}
          transition={{ duration: 2, repeat: Infinity }}
        />
        <span className="font-mono text-sm font-medium tracking-[0.3em] text-spark-text">
          S.P.A.R.K
        </span>
      </div>

      {/* Navigation */}
      <nav className="flex-1 px-3 py-4 space-y-1">
        {navItems.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            className={({ isActive }) =>
              `flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm transition-all ${
                isActive
                  ? 'bg-spark-accent-dim text-spark-accent'
                  : 'text-spark-muted hover:bg-spark-accent-dim hover:text-spark-text'
              }`
            }
          >
            <item.icon size={18} strokeWidth={1.5} />
            <span>{item.label}</span>
          </NavLink>
        ))}
      </nav>

      {/* Status */}
      <div className="p-4 border-t border-spark-border">
        <div className="flex items-center gap-2 text-xs text-spark-muted">
          <Radio size={12} className="text-green-500" />
          <span>System Online</span>
        </div>
      </div>
    </aside>
  )
}
