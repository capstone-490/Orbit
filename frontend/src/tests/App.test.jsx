import { cleanup, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it } from 'vitest'
import App from '../App'

afterEach(() => {
  cleanup()
  window.history.pushState({}, '', '/')
})

describe('App routes', () => {
  it('renders the create account page at its route', () => {
    window.history.pushState({}, '', '/create-account')

    render(<App />)

    expect(
      screen.getByRole('heading', { name: /create your account/i })
    ).toBeInTheDocument()

    expect(
      screen.getByRole('button', { name: /create account/i })
    ).toBeInTheDocument()
  })

  it('renders the book a meeting page at its route', () => {
    window.history.pushState({}, '', '/book-meeting')

    render(<App />)

    expect(screen.getByText(/book a meeting page is a placeholder/i)).toBeInTheDocument()
  })
})
