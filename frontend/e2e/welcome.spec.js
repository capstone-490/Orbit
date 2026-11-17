import { expect, test } from './fixtures.js'

const HOME_HEADING = 'Your advisory practice, all in one place.'

const cards = [
  { name: 'Advisor Login', path: '/login', heading: 'Welcome to Orbit' },
  { name: 'Advisor Registration', path: '/create-account', heading: 'Create your account' },
  { name: 'Public Booking', path: '/book-meeting', heading: 'Who would you like to meet with?' },
]

const escapeRegex = (value) => value.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
const createUrlMatcher = (route) => new RegExp(`${escapeRegex(route)}$`)

test.describe('Welcome page', () => {
  test('displays the main heading without browser errors', async ({ page }) => {
    const errors = []
    page.on('console', (message) => {
      if (message.type() === 'error') errors.push(message.text())
    })
    page.on('pageerror', (err) => errors.push(err.message))

    await page.goto('/')

    await expect(page.getByRole('heading', { name: HOME_HEADING })).toBeVisible()
    await page.waitForLoadState('networkidle')
    expect(errors, 'console errors on /').toEqual([])
  })

  for (const card of cards) {
    test(`"${card.name}" card goes to ${card.path} and back returns to /`, async ({ page }) => {
      await page.goto('/')

      await page.getByRole('link', { name: new RegExp(`^${escapeRegex(card.name)}`) }).click()

      await expect(page).toHaveURL(createUrlMatcher(card.path))
      await expect(page.getByRole('heading', { name: card.heading })).toBeVisible()

      await page.goBack()

      await expect(page).toHaveURL(createUrlMatcher('/'))
      await expect(page.getByRole('heading', { name: HOME_HEADING })).toBeVisible()
    })
  }
})
