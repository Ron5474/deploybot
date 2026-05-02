import { useState } from 'react'
import './LandingPage.css'

function LandingPage({ onEnter }) {
  const [name, setName] = useState('')

  const handleSubmit = (e) => {
    e.preventDefault()
    const trimmed = name.trim()
    if (!trimmed) return
    localStorage.setItem('deploybot_username', trimmed)
    onEnter(trimmed)
  }

  return (
    <div className="landing">
      <div className="landing-card">
        <div className="landing-logo">🚀</div>
        <h1 className="landing-title">Welcome to DeployBot</h1>
        <p className="landing-subtitle">Your AI assistant for self-hosting open-source apps</p>
        <form className="landing-form" onSubmit={handleSubmit}>
          <input
            className="landing-input"
            type="text"
            placeholder="Enter your name to get started"
            value={name}
            onChange={e => setName(e.target.value)}
            autoFocus
          />
          <button className="landing-btn" type="submit" disabled={!name.trim()}>
            Start chatting
          </button>
        </form>
      </div>
    </div>
  )
}

export default LandingPage
