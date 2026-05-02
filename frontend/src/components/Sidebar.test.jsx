import { render, screen, fireEvent } from '@testing-library/react'
import Sidebar from './Sidebar'

const defaultProps = {
  isOpen: true,
  onToggle: () => {},
  onNewChat: () => {},
}

test('renders DeployBot logo text when open', () => {
  render(<Sidebar {...defaultProps} />)
  expect(screen.getByText('DeployBot')).toBeInTheDocument()
})

test('renders New chat button when open', () => {
  render(<Sidebar {...defaultProps} />)
  expect(screen.getByText('New chat')).toBeInTheDocument()
})

test('calls onToggle when toggle button clicked', () => {
  const onToggle = vi.fn()
  render(<Sidebar {...defaultProps} onToggle={onToggle} />)
  fireEvent.click(screen.getByRole('button', { name: /toggle sidebar/i }))
  expect(onToggle).toHaveBeenCalledTimes(1)
})

test('calls onNewChat when New chat clicked', () => {
  const onNewChat = vi.fn()
  render(<Sidebar {...defaultProps} onNewChat={onNewChat} />)
  fireEvent.click(screen.getByText('New chat'))
  expect(onNewChat).toHaveBeenCalledTimes(1)
})

test('hides content when closed', () => {
  render(<Sidebar {...defaultProps} isOpen={false} />)
  expect(screen.queryByText('New chat')).not.toBeInTheDocument()
})
