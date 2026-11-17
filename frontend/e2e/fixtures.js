// Substantial AI assistance used;

import { randomUUID } from 'node:crypto'
import { test as base, expect } from '@playwright/test'

// Application endpoints and test configuration
export const API_URL = 'http://127.0.0.1:8001'
const FRONTEND_URL = 'http://127.0.0.1:5173'

const REGISTER_ENDPOINT = '/auth/register'
const LOGIN_ENDPOINT = '/auth/login'
const CURRENT_USER_ENDPOINT = '/auth/me'
const TEST_PASSWORD = 'E2e-test-password-123!'

// Send the frontend's Origin so CORS/origin checks behave like the real app
const headers = { Origin: FRONTEND_URL }

// Unique test-only advisor details, so tests never collide.
export function makeAdvisor(label = 'advisor') {
  const id = randomUUID().slice(0, 8)
  return {
    username: `${label}_${id}`,
    email: `${label}-${id}@example.com`.toLowerCase(),
    password: TEST_PASSWORD,
  }
}

// Registers a new advisor through the authentication API
export async function registerAdvisor(request, advisor) {
  const res = await request.post(`${API_URL}${REGISTER_ENDPOINT}`, {
    headers,
    data: advisor,
  })
  await expect(res, `register ${advisor.email}`).toBeOK()
  return res
}

// Authenticates an existing advisor
export async function loginAdvisor(request, advisor) {
  const res = await request.post(`${API_URL}${LOGIN_ENDPOINT}`, {
    headers,
    data: { email: advisor.email, password: advisor.password },
  })
  await expect(res, `login ${advisor.email}`).toBeOK()
  return res
}

// Retrieves the currently authenticated advisor's account information
export async function getCurrentAdvisor(request) {
  const res = await request.get(`${API_URL}${CURRENT_USER_ENDPOINT}`, { headers })
  await expect(res, 'GET /auth/me').toBeOK()
  const me = await res.json()
  expect(me.id, '/auth/me should return an id').toBeTruthy()
  return me
}

// Checks that invalid or unregistered credentials cannot authenticate
export async function expectCannotLogin(request, email, password) {
  const res = await request.post(`${API_URL}${LOGIN_ENDPOINT}`, {
    headers,
    data: { email, password },
  })
  expect(res.ok(), `login should fail for ${email}`).toBe(false)
}

export const test = base.extend({
  advisor: async ({ context }, use) => {
    const advisorDetails = makeAdvisor('advisor')
    await registerAdvisor(context.request, advisorDetails)
    await loginAdvisor(context.request, advisorDetails)
    const account = await getCurrentAdvisor(context.request)
    await use({ ...advisorDetails, id: account.id })
  },

  /**
   * A second, separate advisor with its own browser context and page
   * (separate cookies), for sharing and permission tests.
   */
  secondAdvisor: async ({ browser, baseURL, timezoneId, locale, permissions }, use) => {
    const secondContext = await browser.newContext({
      baseURL,
      timezoneId,
      locale,
      permissions,
    })
    const secondAdvisorDetails = makeAdvisor('advisor2')
    await registerAdvisor(secondContext.request, secondAdvisorDetails)
    await loginAdvisor(secondContext.request, secondAdvisorDetails)
    const secondAccount = await getCurrentAdvisor(secondContext.request)
    const secondPage = await secondContext.newPage()

    await use({
      ...secondAdvisorDetails,
      id: secondAccount.id,
      context: secondContext,
      page: secondPage,
    })

    await secondContext.close()
  },
})

export { expect }
