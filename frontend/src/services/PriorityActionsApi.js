// Substantial AI assistance used; verified with frontend tests.
import { API_BASE_URL, withAuthCredentials } from './AuthApi'

async function request(path) {
  const response = await fetch(`${API_BASE_URL}${path}`, withAuthCredentials())

  if (!response.ok) {
    const error = new Error(`Request failed with status ${response.status}`)
    error.status = response.status
    throw error
  }

  return response.json()
}

export function getPriorityActions(limit = 5) {
  return request(`/priority-actions?limit=${limit}`)
}

export function getPriorityActionSuggestions() {
  return request('/priority-actions/suggestions')
}

export function getFollowUp(followUpId) {
  return request(`/follow-ups/${followUpId}`)
}