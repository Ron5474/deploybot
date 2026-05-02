import { render, screen, fireEvent } from '@testing-library/react'
import StrategySelector from './StrategySelector'

test('displays current strategy name', () => {
  render(<StrategySelector strategy="regular" onStrategyChange={() => {}} />)
  expect(screen.getByText('Regular')).toBeInTheDocument()
})

test('opens dropdown when pill clicked', () => {
  render(<StrategySelector strategy="regular" onStrategyChange={() => {}} />)
  fireEvent.click(screen.getByText('Regular'))
  expect(screen.getByText('Self Reflection')).toBeInTheDocument()
  expect(screen.getByText('Meta Prompting')).toBeInTheDocument()
  expect(screen.getByText('Prompt Chaining')).toBeInTheDocument()
})

test('calls onStrategyChange with correct id when item selected', () => {
  const onChange = vi.fn()
  render(<StrategySelector strategy="regular" onStrategyChange={onChange} />)
  fireEvent.click(screen.getByText('Regular'))
  fireEvent.click(screen.getByText('Self Reflection'))
  expect(onChange).toHaveBeenCalledWith('self-reflection')
})

test('closes dropdown after selection', () => {
  render(<StrategySelector strategy="regular" onStrategyChange={() => {}} />)
  fireEvent.click(screen.getByText('Regular'))
  fireEvent.click(screen.getByText('Meta Prompting'))
  expect(screen.queryByText('Self Reflection')).not.toBeInTheDocument()
})

test('shows check icon next to selected strategy', () => {
  render(<StrategySelector strategy="self-reflection" onStrategyChange={() => {}} />)
  fireEvent.click(screen.getByText('Self Reflection'))
  // The selected item has a Check icon — verify the item is in the list and marked
  const items = screen.getAllByRole('button')
  const selfReflectBtn = items.find(btn => btn.textContent.includes('Self Reflection'))
  expect(selfReflectBtn).toHaveClass('strategy-item--selected')
})
