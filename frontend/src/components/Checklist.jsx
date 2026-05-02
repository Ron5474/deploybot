import { useState, useEffect } from 'react'
import { ShieldCheck } from 'lucide-react'
import './Checklist.css'

function Checklist({ compose, cacheKey }) {
  const [items, setItems] = useState([])
  const [checked, setChecked] = useState({})
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const stored = localStorage.getItem(`checklist_${cacheKey}`)
    if (stored) {
      const parsed = JSON.parse(stored)
      setItems(parsed.items)
      setChecked(parsed.checked)
      setLoading(false)
      return
    }

    fetch('/checklist', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ compose }),
    })
      .then(r => r.json())
      .then(data => {
        setItems(data.items)
        setLoading(false)
        localStorage.setItem(`checklist_${cacheKey}`, JSON.stringify({ items: data.items, checked: {} }))
      })
      .catch(() => setLoading(false))
  }, [cacheKey])

  const toggle = (i) => {
    const updated = { ...checked, [i]: !checked[i] }
    setChecked(updated)
    localStorage.setItem(`checklist_${cacheKey}`, JSON.stringify({ items, checked: updated }))
  }

  if (loading) return <div className="checklist-loading">Generating deployment checklist...</div>
  if (!items.length) return null

  const done = Object.values(checked).filter(Boolean).length

  return (
    <div className="checklist">
      <div className="checklist-header">
        <ShieldCheck size={14} />
        <span>Deployment Checklist</span>
        <span className="checklist-progress">{done}/{items.length} done</span>
      </div>
      <ul className="checklist-items">
        {items.map((item, i) => (
          <li key={i} className={`checklist-item ${checked[i] ? 'checklist-item--done' : ''}`} onClick={() => toggle(i)}>
            <span className="checklist-box">{checked[i] ? '✓' : ''}</span>
            <span>{item}</span>
          </li>
        ))}
      </ul>
    </div>
  )
}

export default Checklist
