import { useState, useRef, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Send, Mic, Loader2 } from 'lucide-react'

interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  timestamp: Date
  intent?: string
}

export default function ChatPage() {
  const [messages, setMessages] = useState<Message[]>([
    {
      id: '1',
      role: 'assistant',
      content: 'Good evening, Sooraj. All systems nominal. How can I assist you?',
      timestamp: new Date(),
      intent: 'conversation',
    },
  ])
  const [input, setInput] = useState('')
  const [isThinking, setIsThinking] = useState(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const sendMessage = async () => {
    if (!input.trim() || isThinking) return

    const userMessage: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: input.trim(),
      timestamp: new Date(),
    }

    setMessages((prev) => [...prev, userMessage])
    setInput('')
    setIsThinking(true)

    try {
      const response = await fetch('/api/command', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ input: userMessage.content }),
      })

      const data = await response.json()

      const assistantMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: data.reply || 'No response received.',
        timestamp: new Date(),
        intent: data.action,
      }

      setMessages((prev) => [...prev, assistantMessage])
    } catch (error) {
      const errorMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: `Connection error: ${error instanceof Error ? error.message : 'Unknown error'}`,
        timestamp: new Date(),
        intent: 'error',
      }
      setMessages((prev) => [...prev, errorMessage])
    } finally {
      setIsThinking(false)
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      sendMessage()
    }
  }

  return (
    <div className="flex flex-col h-full">
      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-6 space-y-4">
        <AnimatePresence>
          {messages.map((message) => (
            <motion.div
              key={message.id}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.2 }}
              className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
            >
              <div className={`max-w-[70%] ${message.role === 'user' ? 'order-2' : ''}`}>
                {/* Header */}
                <div className="flex items-center gap-2 mb-1 font-mono text-[10px] text-spark-dim">
                  <span>{message.role === 'assistant' ? 'S.P.A.R.K' : 'Sooraj'}</span>
                  <span>{message.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>
                  {message.intent && message.intent !== 'conversation' && (
                    <span className="px-2 py-0.5 bg-spark-accent-dim text-spark-accent rounded text-[9px] uppercase">
                      {message.intent}
                    </span>
                  )}
                </div>

                {/* Bubble */}
                <div
                  className={`px-4 py-3 rounded-xl text-sm leading-relaxed ${
                    message.role === 'assistant'
                      ? 'bg-[#111820] border border-spark-border text-spark-text'
                      : 'bg-white/[0.03] border border-white/[0.05] text-spark-text'
                  } ${message.intent === 'error' ? 'bg-red-500/10 border-red-500/20 text-red-300' : ''}`}
                >
                  {message.content}
                </div>
              </div>
            </motion.div>
          ))}
        </AnimatePresence>

        {/* Thinking Indicator */}
        {isThinking && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="flex justify-start"
          >
            <div className="flex items-center gap-2 px-4 py-3 bg-[#111820] border border-spark-border rounded-xl">
              <div className="flex gap-1">
                {[0, 1, 2, 3, 4].map((i) => (
                  <motion.div
                    key={i}
                    className="w-1 h-4 bg-spark-accent rounded-full"
                    animate={{ height: [8, 20, 8], opacity: [0.4, 1, 0.4] }}
                    transition={{ duration: 1.2, repeat: Infinity, delay: i * 0.1 }}
                  />
                ))}
              </div>
              <span className="text-xs text-spark-muted ml-2">Thinking...</span>
            </div>
          </motion.div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input Bar */}
      <div className="p-4 border-t border-spark-border bg-[#0d1117]">
        <div className="flex items-center gap-3 max-w-4xl mx-auto">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Type a message..."
            className="flex-1 bg-transparent border border-transparent focus:border-spark-accent/30 rounded-lg px-4 py-3 text-sm text-spark-text placeholder-spark-dim outline-none transition-colors"
            disabled={isThinking}
          />
          <button
            onClick={sendMessage}
            disabled={!input.trim() || isThinking}
            className="p-3 rounded-full border border-spark-border text-spark-muted hover:text-spark-accent hover:border-spark-accent transition-all disabled:opacity-50"
          >
            {isThinking ? <Loader2 size={18} className="animate-spin" /> : <Send size={18} />}
          </button>
        </div>
      </div>
    </div>
  )
}
