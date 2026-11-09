// Substantial AI assistance used; verified with frontend tests and production build.
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, useLocation } from 'react-router-dom'
import { afterEach, describe, expect, it, vi } from 'vitest'
import Navbar from '../components/dashboard/Navbar'
import { logoutAdvisor } from '../services/AuthApi'

vi.mock('../services/AuthApi', () => ({
  logoutAdvisor: vi.fn(),
}))

afterEach(() => {
  cleanup()
  vi.clearAllMocks()
})

function CurrentPath() {
  const location = useLocation()
  return <span data-testid="current-path">{location.pathname}</span>
}

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

  it('signs out and navigates to login', async () => {
    logoutAdvisor.mockResolvedValue(undefined)
    render(
      <MemoryRouter initialEntries={['/dashboard']}>
        <Navbar user={mockUser} />
        <CurrentPath />
      </MemoryRouter>,
    )

    fireEvent.click(screen.getByRole('button', { name: 'Logout' }))

    await waitFor(() => expect(logoutAdvisor).toHaveBeenCalledOnce())
    expect(await screen.findByTestId('current-path')).toHaveTextContent('/login')
  })
})
