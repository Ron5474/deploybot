import { render, screen } from '@testing-library/react'
import { vi, afterEach } from 'vitest'
import App from './App'

// Stub network: the mount-time fetchConversations() call resolves to an empty
// conversation list so these static-render tests don't hit the network.
beforeEach(() => {
  // App gates the chat UI behind a saved username (App.jsx:199); seed one so
  // these render tests reach the sidebar/topbar/chat view instead of LandingPage.
  localStorage.setItem('deploybot_username', 'Tester')
  global.fetch = vi.fn(() =>
    Promise.resolve({ ok: true, json: () => Promise.resolve([]) })
  )
})

afterEach(() => {
  localStorage.clear()
})

test('renders sidebar', () => {
  render(<App />)
  expect(screen.getByText('DeployBot')).toBeInTheDocument()
})

test('renders strategy selector', () => {
  render(<App />)
  expect(screen.getByText('Regular')).toBeInTheDocument()
})

test('renders model badge', () => {
  render(<App />)
  expect(screen.getByText('Qwen3.6-27B')).toBeInTheDocument()
})

test('renders empty state initially', () => {
  render(<App />)
  expect(screen.getByText('What would you like to self-host?')).toBeInTheDocument()
})
