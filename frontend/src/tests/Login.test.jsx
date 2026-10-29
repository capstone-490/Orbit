// Substantial AI assistance used; verified with frontend tests and production build.
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, useLocation } from 'react-router-dom'
import { afterEach, describe, expect, it, vi } from 'vitest'
import Login from '../pages/Login'

afterEach(() => {
  cleanup()
  vi.restoreAllMocks()
})

function renderLogin() {
  function LocationProbe() {
    const location = useLocation()
    return <span data-testid="location">{location.pathname}</span>
  }

  return render(
    <MemoryRouter>
      <Login />
      <LocationProbe />
    </MemoryRouter>,
  )
}

describe('Login', () => {
  it('renders email and password fields and accepts input', () => {
    renderLogin()

    const email = screen.getByLabelText('Email')
    const password = screen.getByLabelText('Password')
    fireEvent.change(email, { target: { value: 'advisor@example.com' } })
    fireEvent.change(password, { target: { value: 'secret' } })

    expect(email).toHaveValue('advisor@example.com')
    expect(password).toHaveValue('secret')
  })

  it('navigates to the meeting booking placeholder', () => {
    renderLogin()

    fireEvent.click(screen.getByRole('link', { name: 'Book A Meeting' }))

    expect(screen.getByTestId('location')).toHaveTextContent('/book-meeting')
  })

  it('navigates to the account creation placeholder', () => {
    renderLogin()

    fireEvent.click(screen.getByRole('link', { name: 'Create an account' }))

    expect(screen.getByTestId('location')).toHaveTextContent('/create-account')
  })

  it('shows a loading state while the login request is pending', async () => {
    let resolveLogin
    vi.stubGlobal(
      'fetch',
      vi.fn(
        () =>
          new Promise((resolve) => {
            resolveLogin = resolve
          }),
      ),
    )
    renderLogin()

    fireEvent.change(screen.getByLabelText('Email'), {
      target: { value: 'advisor@example.com' },
    })
    fireEvent.change(screen.getByLabelText('Password'), { target: { value: 'secret' } })
    fireEvent.click(screen.getByRole('button', { name: 'Sign In' }))

    expect(screen.getByRole('button', { name: 'Signing in...' })).toBeDisabled()
    resolveLogin({ ok: true, json: async () => ({}) })
    await waitFor(() => expect(screen.getByRole('button', { name: 'Sign In' })).toBeEnabled())
  })

  it('displays the API error when credentials are rejected', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async () => ({
        ok: false,
        json: async () => ({ detail: 'Invalid credentials.' }),
      })),
    )
    renderLogin()

    fireEvent.change(screen.getByLabelText('Email'), {
      target: { value: 'advisor@example.com' },
    })
    fireEvent.change(screen.getByLabelText('Password'), { target: { value: 'wrong' } })
    fireEvent.click(screen.getByRole('button', { name: 'Sign In' }))

    expect(await screen.findByRole('alert')).toHaveTextContent('Invalid credentials.')
  })

  it('navigates to the workspace after a successful login', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async () => ({
        ok: true,
        json: async () => ({ token: 'test-token' }),
      })),
    )
    renderLogin()

    fireEvent.change(screen.getByLabelText('Email'), {
      target: { value: 'advisor@example.com' },
    })
    fireEvent.change(screen.getByLabelText('Password'), { target: { value: 'secret' } })
    fireEvent.click(screen.getByRole('button', { name: 'Sign In' }))

    await waitFor(() => expect(screen.getByTestId('location')).toHaveTextContent('/dashboard'))
    expect(localStorage.getItem('orbit_auth_token')).toBe('test-token')
  })
})
