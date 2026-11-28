
import { API_BASE_URL, withAuthCredentials } from './AuthApi'

async function handleResponse(response, defaultMessage) {
  if (!response.ok) {
    let message = defaultMessage

    try {
      const data = await response.json()

      if (typeof data.detail === 'string') {
        message = data.detail
      } else if (typeof data.message === 'string') {
        message = data.message
      }
    } catch {}

    throw new Error(message)
  }

  return response.json()
}

// Retrieve predefined financial goal options
export async function getGoalTypes() {
  const response = await fetch(
    `${API_BASE_URL}/goals/types`,
    withAuthCredentials(),
  )

  return handleResponse(response, 'Unable to load financial goal options.')
}

// Retrieve saved financial goals for a client
export async function getClientGoals(clientId) {
  const response = await fetch(
    `${API_BASE_URL}/clients/${clientId}/goals`,
    withAuthCredentials(),
  )

  return handleResponse(response, 'Unable to load client goals.')
}

// Save financial goals for a client
export async function createClientGoals(clientId, goals) {
  const response = await fetch(
    `${API_BASE_URL}/clients/${clientId}/goals`,
    withAuthCredentials({
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ goals }),
    }),
  )

  return handleResponse(response, 'Unable to save financial goals.')
}

// Delete a saved financial goal
export async function deleteClientGoal(clientId, goalId) {
  const response = await fetch(
    `${API_BASE_URL}/clients/${clientId}/goals/${goalId}`,
    withAuthCredentials({
      method: 'DELETE',
    }),
  )

  return handleResponse(
    response,
    'Unable to delete financial goal.',
  )
}

