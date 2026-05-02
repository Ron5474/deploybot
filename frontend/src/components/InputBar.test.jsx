import { render, screen, fireEvent } from '@testing-library/react'
import InputBar from './InputBar'

test('renders textarea with placeholder', () => {
  render(<InputBar onSend={() => {}} isLoading={false} />)
  expect(screen.getByPlaceholderText('Ask about self-hosting...')).toBeInTheDocument()
})

test('calls onSend with input text when send button clicked', () => {
  const onSend = vi.fn()
  render(<InputBar onSend={onSend} isLoading={false} />)
  const textarea = screen.getByPlaceholderText('Ask about self-hosting...')
  fireEvent.change(textarea, { target: { value: 'How do I install Docker?' } })
  fireEvent.click(screen.getByRole('button', { name: /send/i }))
  expect(onSend).toHaveBeenCalledWith('How do I install Docker?')
})

test('clears input after send', () => {
  render(<InputBar onSend={() => {}} isLoading={false} />)
  const textarea = screen.getByPlaceholderText('Ask about self-hosting...')
  fireEvent.change(textarea, { target: { value: 'some message' } })
  fireEvent.click(screen.getByRole('button', { name: /send/i }))
  expect(textarea.value).toBe('')
})

test('send button is disabled when input is empty', () => {
  render(<InputBar onSend={() => {}} isLoading={false} />)
  expect(screen.getByRole('button', { name: /send/i })).toBeDisabled()
})

test('send button is disabled while loading', () => {
  render(<InputBar onSend={() => {}} isLoading={true} />)
  expect(screen.getByRole('button', { name: /send/i })).toBeDisabled()
})

test('calls onSend when Enter pressed without Shift', () => {
  const onSend = vi.fn()
  render(<InputBar onSend={onSend} isLoading={false} />)
  const textarea = screen.getByPlaceholderText('Ask about self-hosting...')
  fireEvent.change(textarea, { target: { value: 'test' } })
  fireEvent.keyDown(textarea, { key: 'Enter', shiftKey: false })
  expect(onSend).toHaveBeenCalledWith('test')
})
