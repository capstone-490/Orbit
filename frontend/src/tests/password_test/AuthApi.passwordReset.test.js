import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { API_BASE_URL } from '../../services/AuthApi'
import {
  requestPasswordReset,
  resetPassword,
  validateResetToken,
} from '../../services/AuthApi.passwordReset'

describe('Password Reset API', () => {
  const fetchMock = vi.fn()

  beforeEach(() => {
    vi.stubGlobal('fetch', fetchMock)
    fetchMock.mockReset()
  })

  afterEach(() => {
    vi.unstubAllGlobals()
  })

  describe('requestPasswordReset', () => {
    it('sends the email and returns a successful response', async () => {
      const data = { message: 'If an account exists, a reset link has been sent.' }
      fetchMock.mockResolvedValue({
        ok: true,
        json: vi.fn().mockResolvedValue(data),
      })

      await expect(requestPasswordReset({ email: 'advisor@example.com' })).resolves.toEqual(data)

      expect(fetchMock).toHaveBeenCalledWith(`${API_BASE_URL}/auth/forgot-password`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email: 'advisor@example.com' }),
      })
    })

    it('uses the API error detail when the request fails', async () => {
      fetchMock.mockResolvedValue({
        ok: false,
        json: vi.fn().mockResolvedValue({ detail: 'Invalid email.' }),
      })

      await expect(requestPasswordReset({ email: 'advisor@example.com' })).rejects.toThrow(
        'Invalid email.',
      )
    })

    it('uses the API message when detail is unavailable', async () => {
      fetchMock.mockResolvedValue({
        ok: false,
        json: vi.fn().mockResolvedValue({ message: 'Email service unavailable.' }),
      })

      await expect(requestPasswordReset({ email: 'advisor@example.com' })).rejects.toThrow(
        'Email service unavailable.',
      )
    })

    it('uses the fallback when the error response is not valid JSON', async () => {
      fetchMock.mockResolvedValue({
        ok: false,
        json: vi.fn().mockRejectedValue(new Error('Invalid JSON')),
      })

      await expect(requestPasswordReset({ email: 'advisor@example.com' })).rejects.toThrow(
        'Unable to send the reset link. Please try again.',
      )
    })

    it('propagates network errors', async () => {
      fetchMock.mockRejectedValue(new Error('Network failure'))

      await expect(requestPasswordReset({ email: 'advisor@example.com' })).rejects.toThrow(
        'Network failure',
      )
    })

    it('uses the fallback when detail and message are not strings', async () => {
      fetchMock.mockResolvedValue({
        ok: false,
        json: vi.fn().mockResolvedValue({
          detail: 123,
          message: null,
        }),
      })

      await expect(requestPasswordReset({ email: 'advisor@example.com' })).rejects.toThrow(
        'Unable to send the reset link. Please try again.',
      )
    })
  })

  describe('validateResetToken', () => {
    it('validates the token and returns a successful response', async () => {
      const data = { valid: true }
      fetchMock.mockResolvedValue({
        ok: true,
        json: vi.fn().mockResolvedValue(data),
      })

      await expect(validateResetToken('test token/+')).resolves.toEqual(data)

      expect(fetchMock).toHaveBeenCalledWith(
        `${API_BASE_URL}/auth/reset-password/validate?token=test%20token%2F%2B`,
      )
    })

    it('uses the API error detail when token validation fails', async () => {
      fetchMock.mockResolvedValue({
        ok: false,
        json: vi.fn().mockResolvedValue({ detail: 'Token expired.' }),
      })

      await expect(validateResetToken('expired-token')).rejects.toThrow('Token expired.')
    })

    it('uses the fallback when the error response is not valid JSON', async () => {
      fetchMock.mockResolvedValue({
        ok: false,
        json: vi.fn().mockRejectedValue(new Error('Invalid JSON')),
      })

      await expect(validateResetToken('expired-token')).rejects.toThrow(
        'This reset link is invalid or has expired.',
      )
    })

    it('propagates network errors', async () => {
      fetchMock.mockRejectedValue(new Error('Network failure'))

      await expect(validateResetToken('test-token')).rejects.toThrow('Network failure')
    })
  })

  describe('resetPassword', () => {
    it('sends the token and new password and returns a successful response', async () => {
      const data = { message: 'Password reset successfully.' }
      fetchMock.mockResolvedValue({
        ok: true,
        json: vi.fn().mockResolvedValue(data),
      })

      await expect(
        resetPassword({
          token: 'test-token',
          password: 'NewSecurePassword123!',
        }),
      ).resolves.toEqual(data)

      expect(fetchMock).toHaveBeenCalledWith(`${API_BASE_URL}/auth/reset-password`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          token: 'test-token',
          password: 'NewSecurePassword123!',
        }),
      })
    })

    it('uses the API error detail when the reset fails', async () => {
      fetchMock.mockResolvedValue({
        ok: false,
        json: vi.fn().mockResolvedValue({ detail: 'Token has already been used.' }),
      })

      await expect(
        resetPassword({ token: 'used-token', password: 'NewSecurePassword123!' }),
      ).rejects.toThrow('Token has already been used.')
    })

    it('uses the fallback when the error response is not valid JSON', async () => {
      fetchMock.mockResolvedValue({
        ok: false,
        json: vi.fn().mockRejectedValue(new Error('Invalid JSON')),
      })

      await expect(
        resetPassword({ token: 'test-token', password: 'NewSecurePassword123!' }),
      ).rejects.toThrow('Unable to reset your password. Please try again.')
    })

    it('propagates network errors', async () => {
      fetchMock.mockRejectedValue(new Error('Network failure'))

      await expect(
        resetPassword({ token: 'test-token', password: 'NewSecurePassword123!' }),
      ).rejects.toThrow('Network failure')
    })
  })
})
