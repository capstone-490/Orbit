import { cleanup, render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import ResetPassword from '../../pages/ResetPassword'
import { resetPassword, validateResetToken } from '../../services/AuthApi.passwordReset'

vi.mock('../../services/AuthApi.passwordReset', () => ({
  resetPassword: vi.fn(),
  validateResetToken: vi.fn(),
}))

const VALID_PASSWORD = 'BrandNewPass456!'

function renderPage(url = '/reset-password?token=abc123') {
  return render(
    <MemoryRouter initialEntries={[url]}>
      <Routes>
        <Route path="/reset-password" element={<ResetPassword />} />
        <Route path="/login" element={<p>Login page</p>} />
        <Route path="/forgot-password" element={<p>Forgot page</p>} />
      </Routes>
    </MemoryRouter>,
  )
}

async function fillAndSubmit(user, password, confirmation = password) {
  await user.type(await screen.findByLabelText('New Password'), password)
  await user.type(screen.getByLabelText('Confirm New Password'), confirmation)
  await user.click(screen.getByRole('button', { name: /^reset password$/i }))
}

describe('ResetPassword', () => {
  beforeEach(() => {
    vi.mocked(resetPassword).mockReset()
    vi.mocked(validateResetToken).mockReset()
    vi.mocked(validateResetToken).mockResolvedValue({ message: 'Token is valid.' })
  })

  afterEach(() => {
    cleanup()
  })

  it('checks the reset link and then shows the new password form', async () => {
    renderPage()

    expect(screen.getByText(/verifying your reset link/i)).toBeTruthy()
    expect(await screen.findByLabelText('New Password')).toBeTruthy()
    expect(validateResetToken).toHaveBeenCalledWith('abc123')
  })

  it('shows the invalid-link state when the token is missing', async () => {
    renderPage('/reset-password')

    expect((await screen.findByRole('alert')).textContent).toMatch(/invalid or has expired/i)
    expect(validateResetToken).not.toHaveBeenCalled()
    expect(screen.getByRole('link', { name: /request a new link/i }).getAttribute('href')).toBe(
      '/forgot-password',
    )
  })

  it('shows the API message when the link is expired', async () => {
    vi.mocked(validateResetToken).mockRejectedValue(
      new Error('This reset link is invalid or has expired.'),
    )
    renderPage()

    expect((await screen.findByRole('alert')).textContent).toMatch(/invalid or has expired/i)
    expect(screen.queryByLabelText('New Password')).toBeNull()
  })

  it('rejects passwords that are too short without calling the API', async () => {
    const user = userEvent.setup()
    renderPage()

    await fillAndSubmit(user, 'short')

    expect((await screen.findByRole('alert')).textContent).toMatch(/between 12 and 128/i)
    expect(resetPassword).not.toHaveBeenCalled()
  })

  it('rejects mismatched passwords without calling the API', async () => {
    const user = userEvent.setup()
    renderPage()

    await fillAndSubmit(user, VALID_PASSWORD, 'SomethingElse123!')

    expect((await screen.findByRole('alert')).textContent).toMatch(/do not match/i)
    expect(resetPassword).not.toHaveBeenCalled()
  })

  it('resets the password with the token and shows the success state', async () => {
    vi.mocked(resetPassword).mockResolvedValue({ message: 'done' })
    const user = userEvent.setup()
    renderPage()

    await fillAndSubmit(user, VALID_PASSWORD)

    expect(await screen.findByText(/password reset successfully/i)).toBeTruthy()
    expect(resetPassword).toHaveBeenCalledWith({ token: 'abc123', password: VALID_PASSWORD })

    await user.click(screen.getByRole('button', { name: /go to sign in/i }))
    expect(await screen.findByText('Login page')).toBeTruthy()
  })

  it('shows a loading state while resetting', async () => {
    let resolveReset
    vi.mocked(resetPassword).mockReturnValue(
      new Promise((resolve) => {
        resolveReset = resolve
      }),
    )
    const user = userEvent.setup()
    renderPage()

    await fillAndSubmit(user, VALID_PASSWORD)

    const busyButton = await screen.findByRole('button', { name: /resetting password/i })
    expect(busyButton.disabled).toBe(true)

    resolveReset({ message: 'done' })
    expect(await screen.findByText(/password reset successfully/i)).toBeTruthy()
  })

  it('switches to the invalid-link state if the token expires before submit', async () => {
    vi.mocked(resetPassword).mockRejectedValue(
      new Error('This reset link is invalid or has expired.'),
    )
    const user = userEvent.setup()
    renderPage()

    await fillAndSubmit(user, VALID_PASSWORD)

    expect(await screen.findByRole('link', { name: /request a new link/i })).toBeTruthy()
    expect(screen.queryByLabelText('New Password')).toBeNull()
  })

  it('keeps the form and shows other errors so the advisor can retry', async () => {
    vi.mocked(resetPassword).mockRejectedValue(new Error('Server unavailable'))
    const user = userEvent.setup()
    renderPage()

    await fillAndSubmit(user, VALID_PASSWORD)

    expect((await screen.findByRole('alert')).textContent).toBe('Server unavailable')
    await waitFor(() => {
      expect(screen.getByRole('button', { name: /^reset password$/i }).disabled).toBe(false)
    })
    expect(screen.getByLabelText('New Password')).toBeTruthy()
  })
})
