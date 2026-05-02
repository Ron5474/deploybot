import { useState, useRef, useEffect } from 'react'
import { ArrowUp, Loader2 } from 'lucide-react'
import './InputBar.css'

function InputBar({ onSend, isLoading }) {
  const [input, setInput] = useState('')
  const textareaRef = useRef(null)

  useEffect(() => {
    const textarea = textareaRef.current
    if (!textarea) return
    textarea.style.height = 'auto'
    textarea.style.height = `${Math.min(textarea.scrollHeight, 120)}px`
  }, [input])

  const handleSend = () => {
    if (!input.trim() || isLoading) return
    onSend(input)
    setInput('')
  }

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  return (
    <div className="input-bar">
      <div className="input-container">
        <textarea
          ref={textareaRef}
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Ask about self-hosting..."
          rows={1}
          disabled={isLoading}
        />
        <button onClick={handleSend} disabled={isLoading || !input.trim()} aria-label="Send">
          {isLoading ? <Loader2 size={16} className="spin" /> : <ArrowUp size={16} />}
        </button>
      </div>
      <p className="input-hint">Shift+Enter for new line · Enter to send</p>
    </div>
  )
}

export default InputBar
