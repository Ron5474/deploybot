import { PanelLeftClose, PanelLeftOpen, SquarePen, MessageSquare, Settings, Trash2 } from 'lucide-react'
import './Sidebar.css'

function groupByDate(conversations) {
  const now = new Date()
  const todayStart = new Date(now.getFullYear(), now.getMonth(), now.getDate()).getTime()
  const yesterdayStart = todayStart - 86400000
  const groups = { Today: [], Yesterday: [], Older: [] }
  for (const c of conversations) {
    const t = new Date(c.timestamp.replace(' ', 'T') + 'Z').getTime()
    if (t >= todayStart) groups.Today.push(c)
    else if (t >= yesterdayStart) groups.Yesterday.push(c)
    else groups.Older.push(c)
  }
  return groups
}

function Sidebar({ isOpen, onToggle, onNewChat, conversations = [], activeSessionId, onSelectConversation, onDeleteConversation, username = 'User' }) {
  const groups = groupByDate(conversations)

  return (
    <aside className={`sidebar ${isOpen ? 'sidebar--open' : 'sidebar--closed'}`}>
      <div className="sidebar-header">
        {isOpen && (
          <div className="sidebar-logo">
            <div className="sidebar-logo-icon">🚀</div>
            <span className="sidebar-logo-text">DeployBot</span>
          </div>
        )}
        <button className="sidebar-toggle" onClick={onToggle} aria-label="toggle sidebar">
          {isOpen ? <PanelLeftClose size={16} /> : <PanelLeftOpen size={16} />}
        </button>
      </div>

      {isOpen && (
        <>
          <button className="sidebar-new-chat" onClick={onNewChat}>
            <SquarePen size={14} />
            New chat
          </button>

          {Object.entries(groups).map(([label, items]) =>
            items.length > 0 && (
              <div key={label}>
                <div className="sidebar-section-label">{label}</div>
                {items.map(c => (
                  <div
                    key={c.session_id}
                    className={`sidebar-chat-item ${c.session_id === activeSessionId ? 'sidebar-chat-item--active' : ''}`}
                    onClick={() => onSelectConversation(c.session_id)}
                  >
                    <MessageSquare size={13} />
                    <span>{c.preview}</span>
                    <Trash2
                      size={12}
                      className="sidebar-delete-icon"
                      onClick={e => { e.stopPropagation(); onDeleteConversation(c.session_id) }}
                    />
                  </div>
                ))}
              </div>
            )
          )}

          <div className="sidebar-footer">
            <div className="sidebar-avatar">{username[0].toUpperCase()}</div>
            <span className="sidebar-user-name">{username}</span>
            <Settings size={15} className="sidebar-settings-icon" />
          </div>
        </>
      )}
    </aside>
  )
}

export default Sidebar
