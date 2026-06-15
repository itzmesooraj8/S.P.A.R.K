import { useState } from 'react'
import { motion } from 'framer-motion'
import { Newspaper, RefreshCw, ExternalLink } from 'lucide-react'

const sampleNews = [
  { title: 'Reliance Jio Launches 5G in 31 Cities', source: 'TechCrunch', time: '2h ago' },
  { title: 'Samsung Opens Largest Plant in Noida', source: 'Economic Times', time: '4h ago' },
  { title: 'Indian Government Approves New IT Rules', source: 'NDTV', time: '6h ago' },
  { title: 'Bharat Biotech Receives WHO Prequalification', source: 'Reuters', time: '8h ago' },
]

export default function NewsPage() {
  const [query, setQuery] = useState('')
  const [loading, setLoading] = useState(false)

  const fetchNews = async () => {
    if (!query.trim()) return
    setLoading(true)
    // Simulated - in production this would call the API
    setTimeout(() => setLoading(false), 1500)
  }

  return (
    <div className="p-6 overflow-y-auto h-full">
      <h1 className="text-xl font-mono font-medium mb-6 text-spark-text">News Center</h1>

      {/* Search */}
      <div className="flex gap-3 mb-6">
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && fetchNews()}
          placeholder="Search news topics..."
          className="flex-1 bg-[#111820] border border-spark-border rounded-lg px-4 py-3 text-sm text-spark-text placeholder-spark-dim outline-none focus:border-spark-accent/30"
        />
        <button
          onClick={fetchNews}
          disabled={loading}
          className="px-4 py-3 bg-spark-accent/10 border border-spark-accent/30 rounded-lg text-spark-accent text-sm hover:bg-spark-accent/20 transition-colors flex items-center gap-2"
        >
          <RefreshCw size={16} className={loading ? 'animate-spin' : ''} />
          Search
        </button>
      </div>

      {/* News List */}
      <div className="space-y-3">
        {sampleNews.map((item, i) => (
          <motion.div
            key={i}
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: i * 0.1 }}
            className="p-4 bg-[#111820] border border-spark-border rounded-xl hover:border-spark-accent/20 transition-colors cursor-pointer"
          >
            <div className="flex items-start justify-between">
              <div>
                <h3 className="text-sm font-medium text-spark-text mb-1">{item.title}</h3>
                <div className="flex items-center gap-3 text-xs text-spark-muted">
                  <span>{item.source}</span>
                  <span>•</span>
                  <span>{item.time}</span>
                </div>
              </div>
              <ExternalLink size={14} className="text-spark-dim" />
            </div>
          </motion.div>
        ))}
      </div>
    </div>
  )
}
