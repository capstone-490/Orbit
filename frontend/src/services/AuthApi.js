// Substantial AI assistance used; verified with frontend tests and production build.
const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8001'

export function withAuthCredentials(options = {}) {
  return { ...options, credentials: 'include' }
}

export async function loginAdvisor({ email, password }) {
  const response = await fetch(`${API_BASE_URL}/auth/login`, {
    credentials: 'include',
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ email, password }),
  })

  if (!response.ok) {
    let message = 'Unable to sign in. Check your email and password and try again.'

    try {
      const data = await response.json()
      if (typeof data.detail === 'string') {
        message = data.detail
      } else if (typeof data.message === 'string') {
        message = data.message
      }
    } catch {
      // Use the standard message when the API does not return JSON.
    }

    throw new Error(message)
  }

  return response.json()
}

export async function getCurrentAdvisor() {
  const response = await fetch(`${API_BASE_URL}/auth/me`, {
    credentials: 'include',
  })
  if (!response.ok) throw new Error('Not authenticated')
  return response.json()
}

export async function logoutAdvisor() {
  await fetch(`${API_BASE_URL}/auth/logout`, {
    credentials: 'include',
    method: 'POST',
  })
}
