// Substantial AI assistance used; verified with frontend tests and production build.
import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { MemoryRouter, useLocation } from 'react-router-dom'
import { afterEach, describe, expect, it } from 'vitest'
import BookingTabs from '../../components/booking/BookingTabs'

afterEach(cleanup)

function LocationDisplay() {
  const location = useLocation()
  return <span data-testid="location">{location.pathname}</span>
}

describe('BookingTabs', () => {
  const renderTabs = () =>
    render(
      <MemoryRouter initialEntries={['/book']}>
        <BookingTabs />
        <LocationDisplay />
      </MemoryRouter>,
    )

  it('shows both navigation tabs', () => {
    renderTabs()

    expect(screen.getByRole('button', { name: 'Advisor Login' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Book a Meeting' })).toBeInTheDocument()
  })

  it('highlights the booking tab', () => {
    renderTabs()

    expect(screen.getByRole('button', { name: 'Book a Meeting' })).toHaveClass('active')
  })

  it('navigates to the login page', () => {
    renderTabs()

    fireEvent.click(screen.getByRole('button', { name: 'Advisor Login' }))

    expect(screen.getByTestId('location')).toHaveTextContent('/login')
  })
})
