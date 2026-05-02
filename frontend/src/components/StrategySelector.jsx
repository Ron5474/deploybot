import { useState, useEffect, useRef } from 'react'
import { Zap, RefreshCw, Sparkles, Link, Check, ChevronDown, ChevronUp } from 'lucide-react'
import './StrategySelector.css'

const STRATEGIES = [
  { id: 'regular', label: 'Regular', icon: Zap, description: 'Standard single-pass response' },
  { id: 'self-reflection', label: 'Self Reflection', icon: RefreshCw, description: 'Reviews and improves its own output' },
  { id: 'meta-prompting', label: 'Meta Prompting', icon: Sparkles, description: 'Generates an optimal prompt first' },
  { id: 'prompt-chaining', label: 'Prompt Chaining', icon: Link, description: 'Breaks task into sequential steps' },
]

function StrategySelector({ strategy, onStrategyChange }) {
  const [open, setOpen] = useState(false)
  const ref = useRef(null)

  const current = STRATEGIES.find(s => s.id === strategy) || STRATEGIES[0]

  useEffect(() => {
    const handleClickOutside = (e) => {
      if (ref.current && !ref.current.contains(e.target)) setOpen(false)
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  const toggle = () => setOpen(o => !o)

  return (
    <div className="strategy-selector" ref={ref}>
      {/* Pill wrapper — the entire pill area is clickable */}
      <div
        className={`strategy-pill ${open ? 'strategy-pill--open' : ''}`}
        onClick={toggle}
      >
        <span className="strategy-pill-dot" />
        <span className="strategy-pill-label">Strategy</span>
        {/* Current label text lives here, not inside the <button>, so getAllByRole('button')
            won't pick up this text when looking for dropdown item buttons */}
        <span className="strategy-pill-value">{current.label}</span>
        {open ? <ChevronUp size={11} /> : <ChevronDown size={11} />}
      </div>

      {open && (
        <div className="strategy-dropdown">
          {STRATEGIES.map(({ id, label, icon: Icon, description }) => (
            <button
              key={id}
              className={`strategy-item ${id === strategy ? 'strategy-item--selected' : ''}`}
              onClick={() => { onStrategyChange(id); setOpen(false) }}
            >
              <span className={`strategy-item-icon strategy-item-icon--${id}`}>
                <Icon size={13} />
              </span>
              <span className="strategy-item-body">
                <span className="strategy-item-name">{label}</span>
                <span className="strategy-item-desc">{description}</span>
              </span>
              {id === strategy && <Check size={13} className="strategy-item-check" />}
            </button>
          ))}
        </div>
      )}
    </div>
  )
}

export default StrategySelector
