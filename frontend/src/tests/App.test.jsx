// Substantial AI assistance used; verified with frontend tests.
import { cleanup, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import App from '../App'

afterEach(() => {
  cleanup()
  vi.unstubAllGlobals()
  vi.restoreAllMocks()
  window.history.pushState({}, '', '/')
})

describe('App routes', () => {
  it('renders the create account page at its route', () => {
    window.history.pushState({}, '', '/create-account')

    render(<App />)

    expect(screen.getByText(/create an account page is a placeholder/i)).toBeInTheDocument()
  })

  it('renders the book a meeting page at its route', () => {
    window.history.pushState({}, '', '/book-meeting')

    render(<App />)

    expect(screen.getByText(/book a meeting page is a placeholder/i)).toBeInTheDocument()
  })

  it('redirects unauthenticated users away from advisor pages', async () => {
    window.history.pushState({}, '', '/dashboard')
    vi.stubGlobal('fetch', vi.fn(async () => ({ ok: false })))

    render(<App />)

    expect(await screen.findByText('Welcome to Orbit')).toBeInTheDocument()
    expect(window.location.pathname).toBe('/login')
  })
})
