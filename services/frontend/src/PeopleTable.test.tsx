import { render, screen } from '@testing-library/react'
import { PeopleTable } from './PeopleTable'

it('renders a row', () => {
  render(<PeopleTable rows={[{ id: 1, name: 'Alice' }]} />)
  expect(screen.getByText('Alice')).toBeInTheDocument()
})




