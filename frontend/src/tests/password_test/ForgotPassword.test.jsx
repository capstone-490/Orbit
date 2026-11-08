import { cleanup, render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { requestPasswordReset } from '../services/AuthApi'
import ForgotPassword from './ForgotPassword'

vi.mock('../services/AuthApi', () => ({
  requestPasswordReset: vi.fn(),
}))

function renderPage() {
  return render(
    <MemoryRouter>
      <ForgotPassword />
    </MemoryRouter>,
  )
}

describe('ForgotPassword', () => {
  beforeEach(() => {
    vi.mocked(requestPasswordReset).mockReset()
  })

  afterEach(() => {
    cleanup()
  })

  it('shows an email field and a link back to sign in', () => {
    renderPage()

    expect(screen.getByLabelText('Email')).toBeTruthy()
    expect(screen.getByRole('button', { name: /send reset link/i })).toBeTruthy()
    expect(screen.getByRole('link', { name: /sign in/i }).getAttribute('href')).toBe('/login')
  })

  it('validates that an email was entered', async () => {
    const user = userEvent.setup()
    renderPage()

    await user.click(screen.getByRole('button', { name: /send reset link/i }))

    expect((await screen.findByRole('alert')).textContent).toMatch(/enter your email/i)
    expect(requestPasswordReset).not.toHaveBeenCalled()
  })

  it('validates the email format before calling the API', async () => {
    const user = userEvent.setup()
    renderPage()

    await user.type(screen.getByLabelText('Email'), 'not-an-email')
    await user.click(screen.getByRole('button', { name: /send reset link/i }))

    expect((await screen.findByRole('alert')).textContent).toMatch(/valid email/i)
    expect(requestPasswordReset).not.toHaveBeenCalled()
  })

  it('sends a normalized email and shows the success state', async () => {
    vi.mocked(requestPasswordReset).mockResolvedValue({ message: 'ok' })
    const user = userEvent.setup()
    renderPage()

    await user.type(screen.getByLabelText('Email'), '  Advisor@Example.COM ')
    await user.click(screen.getByRole('button', { name: /send reset link/i }))

    expect(await screen.findByText(/check your email/i)).toBeTruthy()
    expect(requestPasswordReset).toHaveBeenCalledWith({ email: 'advisor@example.com' })
    expect(screen.getByRole('link', { name: /back to sign in/i }).getAttribute('href')).toBe(
      '/login',
    )
  })

  it('shows a loading state while the request is in flight', async () => {
    let resolveRequest
    vi.mocked(requestPasswordReset).mockReturnValue(
      new Promise((resolve) => {
        resolveRequest = resolve
      }),
    )
    const user = userEvent.setup()
    renderPage()

    await user.type(screen.getByLabelText('Email'), 'advisor@example.com')
    await user.click(screen.getByRole('button', { name: /send reset link/i }))

    const busyButton = await screen.findByRole('button', { name: /sending link/i })
    expect(busyButton.disabled).toBe(true)

    resolveRequest({ message: 'ok' })
    expect(await screen.findByText(/check your email/i)).toBeTruthy()
  })

  it('shows an error when the request fails and lets the advisor retry', async () => {
    vi.mocked(requestPasswordReset).mockRejectedValue(new Error('Server unavailable'))
    const user = userEvent.setup()
    renderPage()

    await user.type(screen.getByLabelText('Email'), 'advisor@example.com')
    await user.click(screen.getByRole('button', { name: /send reset link/i }))

    expect((await screen.findByRole('alert')).textContent).toBe('Server unavailable')
    await waitFor(() => {
      expect(screen.getByRole('button', { name: /send reset link/i }).disabled).toBe(false)
    })
  })
})
