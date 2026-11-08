// Password recovery API calls. Append these to services/AuthApi.js
// (they reuse its API_BASE_URL constant).
import { API_BASE_URL } from './AuthApi'

async function readErrorMessage(response, fallback) {
  try {
    const data = await response.json()
    if (typeof data.detail === 'string') return data.detail
    if (typeof data.message === 'string') return data.message
  } catch {
    // Use the fallback when the API does not return JSON.
  }
  return fallback
}

export async function requestPasswordReset({ email }) {
  const response = await fetch(`${API_BASE_URL}/auth/forgot-password`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email }),
  })

  if (!response.ok) {
    throw new Error(
      await readErrorMessage(response, 'Unable to send the reset link. Please try again.'),
    )
  }

  return response.json()
}

export async function validateResetToken(token) {
  const response = await fetch(
    `${API_BASE_URL}/auth/reset-password/validate?token=${encodeURIComponent(token)}`,
  )

  if (!response.ok) {
    throw new Error(
      await readErrorMessage(response, 'This reset link is invalid or has expired.'),
    )
  }

  return response.json()
}

export async function resetPassword({ token, password }) {
  const response = await fetch(`${API_BASE_URL}/auth/reset-password`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ token, password }),
  })

  if (!response.ok) {
    throw new Error(
      await readErrorMessage(response, 'Unable to reset your password. Please try again.'),
    )
  }

  return response.json()
}
