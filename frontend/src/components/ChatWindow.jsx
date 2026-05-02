import { useEffect, useRef } from 'react'
import { Rocket, RefreshCw } from 'lucide-react'
import Message from './Message'
import './ChatWindow.css'

const SUGGESTIONS = [
  'Generate a docker-compose for Gitea with PostgreSQL',
  'Does Immich have any recent CVEs?',
  'What are the best self-hosted alternatives for Google Photos?',
  'How do I set up VaultWarden with TLS?',
]

function ChatWindow({ messages, isLoading, onSend, username = 'User', onRegenerate }) {
  const bottomRef = useRef(null)
  const containerRef = useRef(null)
  const isNearBottom = useRef(true)

  const handleScroll = () => {
    const el = containerRef.current
    if (!el) return
    isNearBottom.current = el.scrollHeight - el.scrollTop - el.clientHeight < 100
  }

  useEffect(() => {
    if (isNearBottom.current) {
      bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
    }
  }, [messages])

  return (
    <div className="chat-window" ref={containerRef} onScroll={handleScroll}>
      {messages.length === 0 ? (
        <div className="empty-state">
          <Rocket size={40} className="empty-icon" />
          <h2>What would you like to self-host?</h2>
          <p>Ask anything about Docker, self-hosted apps, security, and more.</p>
          <div className="suggestions">
            {SUGGESTIONS.map((s, i) => (
              <button key={i} className="suggestion" onClick={() => onSend(s)}>
                {s}
              </button>
            ))}
          </div>
        </div>
      ) : (
        messages.map((msg, i) => (
          <Message
            key={i}
            message={msg}
            username={username}
            isStreaming={isLoading && i === messages.length - 1}
          />
        ))
      )}

      {!isLoading && messages.length > 0 && messages[messages.length - 1]?.role === 'assistant' && (
        <button className="regenerate-btn" onClick={onRegenerate} title="Regenerate response">
          <RefreshCw size={13} />
          Regenerate
        </button>
      )}
      <div ref={bottomRef} />
    </div>
  )
}

export default ChatWindow
