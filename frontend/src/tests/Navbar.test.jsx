import { render, screen, cleanup } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { describe, it, expect, afterEach } from 'vitest'
import Navbar from '../components/dashboard/Navbar'

afterEach(() => {
  cleanup()
})

describe('Navbar', () => {
  const mockUser = {
    role: 'Advisor',
  }

  it('renders the navbar with the logo and user role', () => {
    render(
      <MemoryRouter>
        <Navbar user={mockUser} />
      </MemoryRouter>
    )

    expect(screen.getByAltText('Orbit')).toBeInTheDocument()
    expect(screen.getByText('Orbit')).toBeInTheDocument()
    expect(screen.getByText('Advisor')).toBeInTheDocument()
  })

  it('renders navigation links with the correct routes', () => {
    render(
      <MemoryRouter>
        <Navbar user={mockUser} />
      </MemoryRouter>
    )

    expect(screen.getByRole('link', { name: 'Dashboard' }))
      .toHaveAttribute('href', '/')

    expect(screen.getByRole('link', { name: 'Clients' }))
      .toHaveAttribute('href', '/clients')

    expect(screen.getByRole('link', { name: 'Calendar' }))
      .toHaveAttribute('href', '/calendar')

    expect(screen.getByRole('link', { name: 'Follow-Ups' }))
      .toHaveAttribute('href', '/follow-ups')

    expect(screen.getByRole('link', { name: 'Tasks' }))
      .toHaveAttribute('href', '/tasks')

    expect(screen.getByRole('link', { name: 'Documents' }))
      .toHaveAttribute('href', '/documents')

    expect(screen.getByRole('link', { name: 'AI Review' }))
      .toHaveAttribute('href', '/ai-review')

    expect(screen.getByRole('link', { name: 'Activity' }))
      .toHaveAttribute('href', '/activity')
  })
})