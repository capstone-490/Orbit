// Substantial AI assistance used;

import { expect, test } from './fixtures.js'
import {
  createClient,
  createMeeting,
  createTask,
  daysFromNow,
  MEETING,
  NOW,
  TASK,
} from './helpers/db.js'

// date formatting

// Same formatting the components use (browser runs with locale en-US, timezone UTC)
const formatMeetingDate = (date) => date.toLocaleString('en-US', { timeZone: 'UTC' })
const formatTaskDate = (yyyyMmDd) =>
  new Date(`${yyyyMmDd}T00:00:00Z`)
    .toLocaleDateString('en-US', { month: 'short', day: 'numeric', timeZone: 'UTC' })
    .toUpperCase()

//  dashboard test data
/**
 * Inserts the standard dashboard data set for one advisor:
 * - 2 clients this month + 1 from ~40 days ago (always a previous month)
 * - 4 meetings, one per status, each with its own client so rows are distinguishable
 * - 3 tasks (pending, overdue, done): within the dashboard's 3-task limit
 */
async function createDashboardData(advisorId) {
  const clients = {
    future: await createClient(advisorId),
    overdue: await createClient(advisorId),
    completed: await createClient(advisorId),
    cancelled: await createClient(advisorId, { createdAt: daysFromNow(-40) }),
  }
  // 3 of the 4 clients were created this month

  for (const [meetingType, client] of Object.entries(clients)) {
    await createMeeting(advisorId, client.id, MEETING[meetingType])
  }

  const tasks = {
    pending: await createTask(advisorId, {
      ...TASK.pending,
      title: 'Pending task',
      clientId: clients.future.id,
    }),
    overdue: await createTask(advisorId, { ...TASK.overdue, title: 'Overdue task' }),
    done: await createTask(advisorId, { ...TASK.done, title: 'Done task' }),
  }

  return { clients, tasks }
}

//  dashboard element selectors

const getSummaryCard = (page, name) => page.getByRole('article', { name, exact: true })
const getMeetingRow = (page, client) =>
  page.getByRole('article', { name: `Meeting with ${client.name}`, exact: true })

// dashboard tests

test.describe('Advisor dashboard', () => {
  let dashboardData

  test.beforeEach(async ({ page, advisor }) => {
    dashboardData = await createDashboardData(advisor.id)
    await page.clock.setFixedTime(NOW)
    await page.goto('/dashboard')
    await expect(getSummaryCard(page, 'Total clients')).toBeVisible()
  })

  test('displays accurate totals in the summary cards', async ({ page }) => {
    const clients = getSummaryCard(page, 'Total clients')
    await expect(clients.getByText('4', { exact: true })).toBeVisible()
    await expect(clients).toContainText('+3 this month')

    const meetings = getSummaryCard(page, 'Upcoming meetings')
    await expect(meetings.getByText('1', { exact: true })).toBeVisible()
    await expect(meetings).toContainText(`Next: ${formatMeetingDate(MEETING.future.start)}`)

    const tasks = getSummaryCard(page, 'Pending tasks')
    await expect(tasks.getByText('2', { exact: true })).toBeVisible()
    await expect(tasks).toContainText('1 overdue')
  })

  test('displays the correct status for each meeting', async ({ page }) => {
    const expected = {
      future: 'Scheduled',
      overdue: 'Overdue',
      completed: 'Completed',
      cancelled: 'Cancelled',
    }
    for (const [meetingType, status] of Object.entries(expected)) {
      await expect(
        getMeetingRow(page, dashboardData.clients[meetingType]).getByText(status, { exact: true }),
        `${meetingType} meeting`,
      ).toBeVisible()
    }
  })

  test('shows Reschedule only for the scheduled meeting', async ({ page }) => {
    const reschedule = (meetingType) =>
      getMeetingRow(page, dashboardData.clients[meetingType]).getByRole('button', {
        name: 'Reschedule',
      })

    await expect(reschedule('future')).toBeVisible()
    await expect(reschedule('overdue')).toHaveCount(0)
    await expect(reschedule('completed')).toHaveCount(0)
    await expect(reschedule('cancelled')).toHaveCount(0)
  })

  test('checking a task updates the pending count and survives a reload', async ({ page }) => {
    const pending = getSummaryCard(page, 'Pending tasks')
    const checkbox = page.getByRole('checkbox', { name: 'Complete Pending task' })

    await expect(pending.getByText('2', { exact: true })).toBeVisible()
    const saved = page.waitForResponse(
      (r) =>
        r.request().method() === 'PATCH' &&
        new URL(r.url()).pathname.startsWith('/advisors/tasks/'),
    )
    await checkbox.click()
    const res = await saved
    expect(res.ok(), `PATCH task returned ${res.status()}`).toBe(true)

    await expect(checkbox).toBeChecked()
    await expect(pending.getByText('1', { exact: true })).toBeVisible()

    await page.reload()
    await expect(
      getSummaryCard(page, 'Pending tasks').getByText('1', { exact: true }),
    ).toBeVisible()
    await expect(page.getByRole('checkbox', { name: 'Complete Pending task' })).toBeChecked()
  })

  test('an overdue task shows "OVERDUE · date"', async ({ page }) => {
    await expect(page.getByText(`OVERDUE · ${formatTaskDate(TASK.overdue.dueDate)}`)).toBeVisible()
  })

  test('"View All (N) Tasks" shows the total and goes to /tasks', async ({ page }) => {
    const link = page.getByRole('link', { name: 'View All (3) Tasks' })
    await expect(link).toBeVisible()
    await link.click()
    await expect(page).toHaveURL(/\/tasks$/)
  })
})
