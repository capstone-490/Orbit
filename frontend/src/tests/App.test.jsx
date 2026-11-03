import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import '@testing-library/jest-dom/vitest'
import App from '../App'

vi.mock('../pages/AdvisorDashboard', () => ({
  default: () => <h1>Dashboard page</h1>,
}))

afterEach(() => {
  cleanup()
  window.history.pushState({}, '', '/')
})

describe('App routes', () => {
  it('renders the create account page at its route', () => {
    window.history.pushState({}, '', '/create-account')

    render(<App />)

    expect(screen.getByRole('heading', { name: /create your account/i })).toBeInTheDocument()

    expect(screen.getByRole('button', { name: /create account/i })).toBeInTheDocument()
  })

  it('renders the book a meeting page at its route', () => {
    window.history.pushState({}, '', '/book-meeting')

    render(<App />)

    expect(screen.getByRole('heading', { name: 'Welcome to Orbit' })).toBeInTheDocument()
  })

  it('renders the shared navigation and navigates to each static page', () => {
    window.history.pushState({}, '', '/dashboard')
    render(<App />)

    expect(screen.getByRole('heading', { name: 'Dashboard page' })).toBeInTheDocument()

    const destinations = [
      ['Calendar', 'Calendar'],
      ['Follow-Ups', 'Follow-Ups'],
      ['Tasks', 'Tasks'],
      ['Documents', 'Documents'],
      ['AI Review', 'AI Review'],
      ['Activity', 'Activity'],
    ]

    for (const [linkName, pageName] of destinations) {
      fireEvent.click(screen.getByRole('link', { name: linkName }))
      expect(screen.getByText(pageName)).toBeInTheDocument()
    }

    expect(screen.getByRole('link', { name: 'Dashboard' })).toHaveAttribute('href', '/dashboard')
  })
})
