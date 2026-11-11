import { withAuthCredentials } from './AuthApi'

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8001/api/v1'

async function request(path, options = {}) {
  const response = await fetch(`${API_BASE_URL}${path}`, withAuthCredentials(options))
  if (!response.ok) {
    const data = await response.json().catch(() => ({}))
    throw new Error(
      typeof data.detail === 'string' ? data.detail : 'Unable to complete the follow-up request.',
    )
  }
  return response.status === 204 ? null : response.json()
}

export function getFollowUps() {
  return request('/follow-ups')
}

export function createFollowUp(payload) {
  return request('/follow-ups', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
}

export function updateFollowUp(id, payload) {
  return request(`/follow-ups/${id}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
}

export function updateFollowUpStatus(id, status) {
  return request(`/follow-ups/${id}/status`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ status }),
  })
}
