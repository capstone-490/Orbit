// Substantial AI assistance used; verified with frontend tests and production build.
const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

export async function loginAdvisor({ email, password }) {
  const response = await fetch(`${API_BASE_URL}/auth/login`, {
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
