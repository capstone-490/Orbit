import { afterEach, describe, expect, it, vi } from 'vitest'
import { loginAdvisor } from '../services/AuthApi'

afterEach(() => {
  vi.unstubAllGlobals()
})

describe('loginAdvisor', () => {
  it('uses the API message when credentials are rejected', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async () => ({
        ok: false,
        json: async () => ({ message: 'Please verify your account.' }),
      })),
    )

    await expect(loginAdvisor({ email: 'advisor@example.com', password: 'secret' })).rejects.toThrow(
      'Please verify your account.',
    )
  })

  it('uses the default error when the failed response is not JSON', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async () => ({
        ok: false,
        json: async () => {
          throw new Error('Invalid JSON')
        },
      })),
    )

    await expect(loginAdvisor({ email: 'advisor@example.com', password: 'secret' })).rejects.toThrow(
      'Unable to sign in. Check your email and password and try again.',
    )
  })

  it('uses the default error when the failed response has no message', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async () => ({
        ok: false,
        json: async () => ({}),
      })),
    )

    await expect(loginAdvisor({ email: 'advisor@example.com', password: 'secret' })).rejects.toThrow(
      'Unable to sign in. Check your email and password and try again.',
    )
  })
})
