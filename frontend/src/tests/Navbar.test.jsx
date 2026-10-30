// Substantial AI assistance used; verified with frontend tests and production build.
import { cleanup, render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, describe, expect, it } from 'vitest'
import Navbar from '../components/dashboard/Navbar'

afterEach(() => {
  cleanup()
})

describe('Navbar', () => {
  const mockUser = {
    role: 'Advisor',
  }

  const renderNavbar = () => {
    render(
      <MemoryRouter>
        <Navbar user={mockUser} />
      </MemoryRouter>,
    )
  }

  it('renders the navbar with the logo and user role', () => {
    renderNavbar()

    expect(screen.getByAltText('Orbit')).toBeInTheDocument()
    expect(screen.getByText('Orbit')).toBeInTheDocument()
    expect(screen.getByText('Advisor')).toBeInTheDocument()
  })

  it('renders navigation links with the correct routes', () => {
    renderNavbar()

    const links = [
      ['Dashboard', '/dashboard'],
      ['Clients', '/clients'],
      ['Calendar', '/calendar'],
      ['Follow-Ups', '/follow-ups'],
      ['Tasks', '/tasks'],
      ['Documents', '/documents'],
      ['AI Review', '/ai-review'],
      ['Activity', '/activity'],
    ]

    links.forEach(([name, href]) => {
      expect(screen.getByRole('link', { name })).toHaveAttribute('href', href)
    })
  })
})
