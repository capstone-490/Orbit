import { expect, test } from './fixtures.js'

test('a newly registered advisor can reach the dashboard', async ({ page, advisor: _advisor }) => {
  await page.goto('/dashboard')

  await expect(page.getByRole('article', { name: 'Total clients' })).toBeVisible()
  await expect(page.getByText('Checking session...')).toBeHidden()
  await expect(page).toHaveURL(/\/dashboard$/)
})
