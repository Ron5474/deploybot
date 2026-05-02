import { useState, useMemo } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter'
import { oneDark } from 'react-syntax-highlighter/dist/esm/styles/prism'
import { Bot, Copy, Check } from 'lucide-react'
import Checklist from './Checklist'
import './Message.css'

function extractCompose(content) {
  const match = content.match(/```ya?ml([\s\S]*?)```/i)
  if (!match) return null
  const block = match[1]
  if (/services\s*:/i.test(block)) return block.trim()
  return null
}

function CodeBlock({ language, code }) {
  const [copied, setCopied] = useState(false)

  const handleCopy = () => {
    navigator.clipboard.writeText(code)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <div className="code-block">
      <div className="code-block-header">
        <span className="code-block-lang">{language}</span>
        <button className="code-block-copy" onClick={handleCopy} aria-label="copy code">
          {copied ? <Check size={13} /> : <Copy size={13} />}
          {copied ? 'Copied!' : 'Copy'}
        </button>
      </div>
      <SyntaxHighlighter
        style={oneDark}
        language={language}
        customStyle={{ margin: 0, background: '#020810', borderRadius: 0, fontSize: '0.82rem', lineHeight: 1.65 }}
        codeTagProps={{ style: { fontFamily: "'JetBrains Mono', 'Fira Code', 'Cascadia Code', monospace" } }}
      >
        {code}
      </SyntaxHighlighter>
    </div>
  )
}

function Message({ message, username = 'User', isStreaming = false }) {
  const isUser = message.role === 'user'
  const compose = useMemo(() => !isUser && !isStreaming ? extractCompose(message.content) : null, [message.content, isUser, isStreaming])
  const cacheKey = useMemo(() => {
    if (!compose) return null
    let hash = 0
    for (let i = 0; i < compose.length; i++) {
      hash = ((hash << 5) - hash) + compose.charCodeAt(i)
      hash |= 0
    }
    return Math.abs(hash).toString(36)
  }, [compose])

  return (
    <div className={`message-row ${isUser ? 'message-row--user' : ''}`}>
      <div className={`message-avatar ${isUser ? 'message-avatar--user' : 'message-avatar--bot'}`}>
        {isUser ? username[0].toUpperCase() : <Bot size={14} />}
      </div>
      <div className="message-content">
        <span className={`message-sender ${isUser ? 'message-sender--user' : 'message-sender--bot'}`}>
          {isUser ? 'You' : 'DeployBot'}
        </span>
        {isUser ? (
          <p className="message-text">{message.content}</p>
        ) : (
          <>
            <ReactMarkdown
              remarkPlugins={[remarkGfm]}
              components={{
                pre({ children }) { return <>{children}</> },
                code({ className, children, ...props }) {
                  const match = /language-(\w+)/.exec(className || '')
                  if (match) {
                    return (
                      <CodeBlock
                        language={match[1]}
                        code={String(children).replace(/\n$/, '')}
                      />
                    )
                  }
                  return <code className="inline-code" {...props}>{children}</code>
                },
              }}
            >
              {message.content}
            </ReactMarkdown>
            {isStreaming && (
              <div className="message-typing">
                <span></span><span></span><span></span>
              </div>
            )}
          </>
        )}
        {compose && <Checklist compose={compose} cacheKey={cacheKey} />}
      </div>
    </div>
  )
}

export default Message
