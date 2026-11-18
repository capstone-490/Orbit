// Substantial AI assistance used; verified with frontend tests and production build.
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, useLocation } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import Navbar from '../components/dashboard/Navbar'
import { logoutAdvisor } from '../services/AuthApi'

vi.mock('../services/AuthApi', () => ({
  logoutAdvisor: vi.fn(),
}))

beforeEach(() => {
  vi.clearAllMocks()
  vi.mocked(logoutAdvisor).mockResolvedValue(undefined)
})

afterEach(() => {
  cleanup()
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
    return render(
      <MemoryRouter initialEntries={['/dashboard']}>
        <Navbar user={mockUser} />
        <CurrentPath />
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

  it('opens the hamburger menu when clicked', () => {
    renderNavbar()

    const menuButton = screen.getByRole('button', { name: 'Open menu' })

    expect(menuButton).toHaveAttribute('aria-expanded', 'false')

    fireEvent.click(menuButton)

    expect(screen.getByRole('button', { name: 'Close menu' })).toHaveAttribute(
      'aria-expanded',
      'true',
    )

    expect(document.getElementById('navbar-navigation')).toHaveClass('navbar-content-open')
  })

  it('closes the hamburger menu when clicked again', () => {
    renderNavbar()

    fireEvent.click(screen.getByRole('button', { name: 'Open menu' }))
    fireEvent.click(screen.getByRole('button', { name: 'Close menu' }))

    expect(screen.getByRole('button', { name: 'Open menu' })).toHaveAttribute(
      'aria-expanded',
      'false',
    )

    expect(document.getElementById('navbar-navigation')).not.toHaveClass('navbar-content-open')
  })

  it('closes the menu when a navigation link is clicked', () => {
    renderNavbar()

    fireEvent.click(screen.getByRole('button', { name: 'Open menu' }))

    expect(document.getElementById('navbar-navigation')).toHaveClass('navbar-content-open')

    fireEvent.click(screen.getByRole('link', { name: 'Clients' }))

    expect(document.getElementById('navbar-navigation')).not.toHaveClass('navbar-content-open')

    expect(screen.getByTestId('current-path')).toHaveTextContent('/clients')
  })

  it('signs out and navigates to login', async () => {
    renderNavbar()

    fireEvent.click(screen.getByRole('button', { name: 'Logout' }))

    await waitFor(() => {
      expect(logoutAdvisor).toHaveBeenCalledOnce()
      expect(screen.getByTestId('current-path')).toHaveTextContent('/login')
    })
  })

  it('closes the menu after logout', async () => {
    renderNavbar()

    fireEvent.click(screen.getByRole('button', { name: 'Open menu' }))

    expect(document.getElementById('navbar-navigation')).toHaveClass('navbar-content-open')

    fireEvent.click(screen.getByRole('button', { name: 'Logout' }))

    await waitFor(() => {
      expect(logoutAdvisor).toHaveBeenCalledOnce()

      expect(document.getElementById('navbar-navigation'))
        .not.toHaveClass('navbar-content-open')

      expect(screen.getByTestId('current-path')).toHaveTextContent('/login')
    })
  })
})
