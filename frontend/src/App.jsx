import { useState, useRef, useEffect } from 'react'
import Sidebar from './components/Sidebar'
import ChatWindow from './components/ChatWindow'
import InputBar from './components/InputBar'
import StrategySelector from './components/StrategySelector'
import LandingPage from './components/LandingPage'
import { Download } from 'lucide-react'
import './App.css'

function App() {
  const [messages, setMessages] = useState([])
  const [isLoading, setIsLoading] = useState(false)
  const [sidebarOpen, setSidebarOpen] = useState(true)
  const [strategy, setStrategy] = useState('regular')
  const [conversations, setConversations] = useState([])
  const [username, setUsername] = useState(() => localStorage.getItem('deploybot_username') || '')
  const sessionId = useRef(crypto.randomUUID())
  const clientId = useRef(
    (() => {
      let id = localStorage.getItem('deploybot_client_id')
      if (!id) { id = crypto.randomUUID(); localStorage.setItem('deploybot_client_id', id) }
      return id
    })()
  )

  const fetchConversations = async () => {
    const res = await fetch(`/conversations?client_id=${clientId.current}`)
    const data = await res.json()
    setConversations(data)
  }

  useEffect(() => { fetchConversations() }, [])

  const handleNewChat = () => {
    setMessages([])
    setStrategy('regular')
    sessionId.current = crypto.randomUUID()
  }

  const deleteConversation = async (sid) => {
    await fetch(`/conversations/${sid}`, { method: 'DELETE' })
    if (sessionId.current === sid) handleNewChat()
    fetchConversations()
  }

  const loadConversation = async (sid) => {
    const res = await fetch(`/conversations/${sid}`)
    const data = await res.json()
    setMessages(data.map(m => ({
      role: m.role === 'human' ? 'user' : 'assistant',
      content: m.content,
    })))
    sessionId.current = sid
  }

  const exportConversation = () => {
    if (messages.length === 0) return
    const md = messages.map(m =>
      `### ${m.role === 'user' ? username : 'DeployBot'}\n\n${m.content}`
    ).join('\n\n---\n\n')
    const blob = new Blob([md], { type: 'text/markdown' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `${chatTitle.replace(/[^a-z0-9]/gi, '_')}.md`
    a.click()
    URL.revokeObjectURL(url)
  }

  const streamToMessage = async (response) => {
    const reader = response.body.getReader()
    const decoder = new TextDecoder()
    let buffer = ''
    let rafId = null

    const flush = () => {
      if (buffer) {
        const chunk = buffer
        buffer = ''
        setMessages(prev => {
          const updated = [...prev]
          updated[updated.length - 1] = {
            ...updated[updated.length - 1],
            content: updated[updated.length - 1].content + chunk,
          }
          return updated
        })
      }
      rafId = null
    }

    while (true) {
      const { done, value } = await reader.read()
      if (done) break
      buffer += decoder.decode(value, { stream: true })
      if (!rafId) rafId = requestAnimationFrame(flush)
    }
    if (rafId) cancelAnimationFrame(rafId)
    flush()
  }

  const regenerateLastResponse = async () => {
    if (isLoading || messages.length < 2) return
    const lastUserMsg = [...messages].reverse().find(m => m.role === 'user')
    if (!lastUserMsg) return

    await fetch(`/conversations/${sessionId.current}/last`, { method: 'DELETE' })

    setMessages(prev => [...prev.slice(0, -1), { role: 'assistant', content: '' }])
    setIsLoading(true)

    const url = STRATEGY_URLS[strategy] ?? STRATEGY_URLS['regular']
    try {
      const response = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: lastUserMsg.content, session_id: sessionId.current, client_id: clientId.current }),
      })
      if (strategy === 'regular') {
        await streamToMessage(response)
      } else {
        const data = await response.json()
        setMessages(prev => {
          const updated = [...prev]
          updated[updated.length - 1] = { ...updated[updated.length - 1], content: data.response }
          return updated
        })
      }
    } catch {
      setMessages(prev => {
        const updated = [...prev]
        updated[updated.length - 1] = { ...updated[updated.length - 1], content: 'Error: Could not connect to the server.' }
        return updated
      })
    } finally {
      setIsLoading(false)
    }
  }

  const STRATEGY_URLS = {
    'regular':         '/chat',
    'self-reflection': '/chat/reflect',
    'meta-prompting':  '/chat/meta',
    'prompt-chaining': '/chat/chain',
  }

  const sendMessage = async (input) => {
    if (!input.trim() || isLoading) return

    setMessages(prev => [...prev, { role: 'user', content: input }])
    setMessages(prev => [...prev, { role: 'assistant', content: '' }])
    setIsLoading(true)

    const url = STRATEGY_URLS[strategy] ?? STRATEGY_URLS['regular']

    try {
      const response = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: input, session_id: sessionId.current, client_id: clientId.current }),
      })

      if (strategy === 'regular') {
        await streamToMessage(response)
      } else {
        const data = await response.json()
        setMessages(prev => {
          const updated = [...prev]
          updated[updated.length - 1] = {
            ...updated[updated.length - 1],
            content: data.response,
          }
          return updated
        })
      }
    } catch {
      setMessages(prev => {
        const updated = [...prev]
        updated[updated.length - 1] = {
          ...updated[updated.length - 1],
          content: 'Error: Could not connect to the server.',
        }
        return updated
      })
    } finally {
      setIsLoading(false)
      fetchConversations()
    }
  }

  const chatTitle = messages.length > 0
    ? messages[0].content.slice(0, 45) + (messages[0].content.length > 45 ? '…' : '')
    : 'New conversation'

  if (!username) return <LandingPage onEnter={setUsername} />

  return (
    <div className="app">
      <Sidebar
        isOpen={sidebarOpen}
        onToggle={() => setSidebarOpen(o => !o)}
        onNewChat={handleNewChat}
        conversations={conversations}
        activeSessionId={sessionId.current}
        onSelectConversation={loadConversation}
        onDeleteConversation={deleteConversation}
        username={username}
      />
      <div className="chat-main">
        <div className="chat-topbar">
          <span className="chat-topbar-title">{chatTitle}</span>
          <StrategySelector strategy={strategy} onStrategyChange={setStrategy} />
          {messages.length > 0 && (
            <button className="export-btn" onClick={exportConversation} title="Export as Markdown">
              <Download size={14} />
            </button>
          )}
          <div className="chat-model-badge">
            <span className="chat-model-dot" />
            Qwen3.6-27B
          </div>
        </div>
        <ChatWindow messages={messages} isLoading={isLoading} onSend={sendMessage} username={username} onRegenerate={regenerateLastResponse} />
        <InputBar onSend={sendMessage} isLoading={isLoading} />
      </div>
    </div>
  )
}

export default App
