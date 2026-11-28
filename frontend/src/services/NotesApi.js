import { API_BASE_URL, withAuthCredentials } from './AuthApi'

export async function getClientNotes(clientId) {
  const response = await fetch(
    `${API_BASE_URL}/clients/${clientId}/notes`,
    withAuthCredentials(),
  )

  if (!response.ok) {
    throw new Error('Unable to load client notes.')
  }

  return response.json()
}

export async function createClientNote(clientId, note) {
  const response = await fetch(
    `${API_BASE_URL}/clients/${clientId}/notes`,
    withAuthCredentials({
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(note),
    }),
  )

  if (!response.ok) {
    throw new Error('Unable to create client note.')
  }

  return response.json()
}