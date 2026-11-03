import { afterEach, describe, expect, it, vi } from 'vitest'
import { loginAdvisor, registerAdvisor } from '../services/AuthApi'

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

    await expect(
      loginAdvisor({ email: 'advisor@example.com', password: 'secret' }),
    ).rejects.toThrow('Please verify your account.')
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

    await expect(
      loginAdvisor({ email: 'advisor@example.com', password: 'secret' }),
    ).rejects.toThrow('Unable to sign in. Check your email and password and try again.')
  })

  it('uses the default error when the failed response has no message', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async () => ({
        ok: false,
        json: async () => ({}),
      })),
    )

    await expect(
      loginAdvisor({ email: 'advisor@example.com', password: 'secret' }),
    ).rejects.toThrow('Unable to sign in. Check your email and password and try again.')
  })
})

describe('registerAdvisor', () => {
  const advisor = {
    username: 'testadvisor',
    email: 'advisor@example.com',
    password: 'SecurePassword123!',
  }

  it('sends registration details to the correct API endpoint', async () => {
    const responseData = {
      id: 1,
      username: 'testadvisor',
      email: 'advisor@example.com',
    }

    const fetchMock = vi.fn(async () => ({
      ok: true,
      json: async () => responseData,
    }))

    vi.stubGlobal('fetch', fetchMock)

    await expect(registerAdvisor(advisor)).resolves.toEqual(responseData)

    expect(fetchMock).toHaveBeenCalledWith('http://localhost:8001/auth/register', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(advisor),
    })
  })

  it('displays the backend error when an email is already registered', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async () => ({
        ok: false,
        json: async () => ({
          detail: 'An advisor with this email already exists.',
        }),
      })),
    )

    await expect(registerAdvisor(advisor)).rejects.toThrow(
      'An advisor with this email already exists.',
    )
  })

  it('uses the default error when the backend provides no detail', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async () => ({
        ok: false,
        json: async () => ({}),
      })),
    )

    await expect(registerAdvisor(advisor)).rejects.toThrow(
      'Unable to create your account. Please try again.',
    )
  })

  it('uses the default error when the backend returns invalid JSON', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async () => ({
        ok: false,
        json: async () => {
          throw new Error('Invalid JSON')
        },
      })),
    )

    await expect(registerAdvisor(advisor)).rejects.toThrow(
      'Unable to create your account. Please try again.',
    )
  })
})
