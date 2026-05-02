import { render, screen, fireEvent } from '@testing-library/react'
import ChatWindow from './ChatWindow'

test('renders empty state heading when no messages', () => {
  render(<ChatWindow messages={[]} isLoading={false} onSend={() => {}} />)
  expect(screen.getByText('What would you like to self-host?')).toBeInTheDocument()
})

test('renders all four suggestion chips', () => {
  render(<ChatWindow messages={[]} isLoading={false} onSend={() => {}} />)
  expect(screen.getByText('Generate a docker-compose for Gitea with PostgreSQL')).toBeInTheDocument()
  expect(screen.getByText('Does Immich have any recent CVEs?')).toBeInTheDocument()
})

test('calls onSend with suggestion text when chip clicked', () => {
  const onSend = vi.fn()
  render(<ChatWindow messages={[]} isLoading={false} onSend={onSend} />)
  fireEvent.click(screen.getByText('Does Immich have any recent CVEs?'))
  expect(onSend).toHaveBeenCalledWith('Does Immich have any recent CVEs?')
})

test('renders messages when messages array is not empty', () => {
  const messages = [
    { role: 'user', content: 'Hello' },
    { role: 'assistant', content: 'Hi there' },
  ]
  render(<ChatWindow messages={messages} isLoading={false} onSend={() => {}} />)
  expect(screen.getByText('Hello')).toBeInTheDocument()
  expect(screen.queryByText('What would you like to self-host?')).not.toBeInTheDocument()
})

test('shows typing indicator when loading with empty last message', () => {
  const messages = [
    { role: 'user', content: 'Hello' },
    { role: 'assistant', content: '' },
  ]
  const { container } = render(<ChatWindow messages={messages} isLoading={true} onSend={() => {}} />)
  expect(container.querySelector('.typing-indicator')).toBeInTheDocument()
})
