import { render, screen, fireEvent, waitFor, act } from '@testing-library/react'
import { vi } from 'vitest'
import Message from './Message'

beforeEach(() => {
  Object.defineProperty(navigator, 'clipboard', {
    value: { writeText: vi.fn().mockResolvedValue(undefined) },
    configurable: true,
    writable: true,
  })
})

test('renders user message with "You" sender label', () => {
  render(<Message message={{ role: 'user', content: 'Hello there' }} />)
  expect(screen.getByText('You')).toBeInTheDocument()
  expect(screen.getByText('Hello there')).toBeInTheDocument()
})

test('renders assistant message with "DeployBot" sender label', () => {
  render(<Message message={{ role: 'assistant', content: 'Hi! How can I help?' }} />)
  expect(screen.getByText('DeployBot')).toBeInTheDocument()
  expect(screen.getByText('Hi! How can I help?')).toBeInTheDocument()
})

test('user row has --user class', () => {
  const { container } = render(<Message message={{ role: 'user', content: 'test' }} />)
  expect(container.firstChild).toHaveClass('message-row--user')
})

test('renders copy button for fenced code blocks', () => {
  const content = '```yaml\nservices:\n  app:\n    image: nginx\n```'
  render(<Message message={{ role: 'assistant', content }} />)
  expect(screen.getByRole('button', { name: /copy code/i })).toBeInTheDocument()
})

test('copy button writes code to clipboard', async () => {
  const code = 'services:\n  app:\n    image: nginx'
  const content = `\`\`\`yaml\n${code}\n\`\`\``
  render(<Message message={{ role: 'assistant', content }} />)
  fireEvent.click(screen.getByRole('button', { name: /copy code/i }))
  expect(navigator.clipboard.writeText).toHaveBeenCalledWith(code)
})

test('copy button shows Copied! text for 2s after click', async () => {
  vi.useFakeTimers()
  const content = '```bash\necho hello\n```'
  render(<Message message={{ role: 'assistant', content }} />)
  fireEvent.click(screen.getByRole('button', { name: /copy code/i }))
  expect(screen.getByText('Copied!')).toBeInTheDocument()
  await act(async () => { vi.advanceTimersByTime(2001) })
  expect(screen.queryByText('Copied!')).not.toBeInTheDocument()
  vi.useRealTimers()
})
