import { render, screen } from '@testing-library/react'
import { vi } from 'vitest'
import App from './App'

// Silence fetch errors in jsdom
beforeEach(() => {
  global.fetch = vi.fn(() => Promise.reject(new Error('network')))
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
  expect(screen.getByText('claude-sonnet-4-6')).toBeInTheDocument()
})

test('renders empty state initially', () => {
  render(<App />)
  expect(screen.getByText('What would you like to self-host?')).toBeInTheDocument()
})
