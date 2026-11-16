// Substantial AI assistance used;

import { API_URL, expect, test } from './fixtures.js'
import { createClient, createFollowUp, dateOnlyFromNow, FOLLOW_UP, NOW } from './helpers/db.js'

const MESSAGES = {
  empty: 'No follow-ups match your filters.',
  emailCopied: 'Email copied to clipboard.',
  notesSaved: 'Discussion notes saved.',
  unauthorizedClient: 'Client not found or not assigned to this advisor.',
}

//  page helpers

async function openFollowUpTracker(page) {
  await page.clock.setFixedTime(NOW)
  await page.goto('/follow-ups')
  await expect(page.getByRole('heading', { name: 'Follow-Up Tracker' })).toBeVisible()
  await expect(page.getByText('Loading follow-ups...')).toBeHidden()
}

// Locate the form using its heading.
function getFollowUpForm(page, heading = 'New Follow-Up') {
  return page.locator('form').filter({ has: page.getByRole('heading', { name: heading }) })
}

const getClientRow = (page, client) => page.getByRole('row').filter({ hasText: client.name })
const getFollowUpRows = (page) =>
  page.getByRole('row').filter({ hasNot: page.getByRole('columnheader') })

const summaryCard = (page, label) =>
  page
    .getByRole('region', { name: 'Follow-up summary' })
    .getByRole('article')
    .filter({ hasText: label })

async function expectSummaryCounts(page, { overdue, today, upcoming }) {
  await expect(
    summaryCard(page, 'Overdue outreach').getByText(String(overdue), { exact: true }),
  ).toBeVisible()
  await expect(
    summaryCard(page, 'Due today').getByText(String(today), { exact: true }),
  ).toBeVisible()
  await expect(
    summaryCard(page, 'Upcoming').getByText(String(upcoming), { exact: true }),
  ).toBeVisible()
}

const getFilterTab = (page, name) => page.getByRole('button', { name, exact: true })
const search = (page) => page.getByRole('textbox', { name: 'Filter follow-ups' })

// Wait for a successful update to a specific follow-up.
const waitForFollowUpUpdate = (page, id) =>
  page.waitForResponse(
    (r) =>
      r.request().method() === 'PATCH' &&
      new URL(r.url()).pathname.startsWith(`/follow-ups/${id}`) &&
      r.ok(),
  )

async function fillNewFollowUp(page, { client, reason, stage, dueDate }) {
  const form = getFollowUpForm(page)
  if (client)
    await form.getByRole('combobox', { name: /^Client/ }).selectOption({ value: String(client.id) })
  if (reason !== undefined) await form.getByRole('textbox', { name: 'Reason' }).fill(reason)
  if (stage) await form.getByRole('combobox', { name: /^Planning stage/ }).selectOption(stage)
  if (dueDate) await form.getByLabel('Due date', { exact: true }).fill(dueDate)
}

const openNew = async (page) => {
  await page.getByRole('button', { name: 'New Follow-Up' }).click()
  await expect(getFollowUpForm(page)).toBeVisible()
}

// tests

test.describe('Follow-Up Tracker', () => {
  test.describe('create', () => {
    test('creates a follow-up with default priority and status', async ({ page, advisor }) => {
      const client = await createClient(advisor.id)
      const dueDate = dateOnlyFromNow(7)
      await openFollowUpTracker(page)

      await openNew(page)
      await fillNewFollowUp(page, {
        client,
        reason: 'Review FNA results',
        stage: 'Financial Needs Analysis',
        dueDate,
      })
      await getFollowUpForm(page).getByRole('button', { name: 'Create follow-up' }).click()

      await expect(getFollowUpForm(page)).toBeHidden()
      const r = getClientRow(page, client)
      await expect(r).toContainText(client.email)
      await expect(r).toContainText('Review FNA results')

      const stageSelect = r.getByRole('combobox', { name: `Planning stage for ${client.name}` })
      await expect(stageSelect).toHaveValue('Financial Needs Analysis')
      expect(await stageSelect.evaluate((el) => el.selectedOptions[0].textContent)).toBe('FNA')

      await expect(r.getByLabel(`Due date for ${client.name}`)).toHaveValue(dueDate)
      await expect(r.getByRole('combobox', { name: `Priority for ${client.name}` })).toHaveValue(
        'Medium',
      )
      await expect(r.getByRole('combobox', { name: `Status for ${client.name}` })).toHaveValue(
        'Pending',
      )

      await page.reload()
      await expect(getClientRow(page, client)).toContainText('Review FNA results')
    })

    test('selecting a client displays their contact information', async ({ page, advisor }) => {
      const client = await createClient(advisor.id)
      await openFollowUpTracker(page)
      await openNew(page)
      await fillNewFollowUp(page, { client })

      const card = getFollowUpForm(page).getByRole('region', { name: 'Client contact information' })
      await expect(card).toContainText(client.name)
      await expect(card.getByRole('link', { name: client.email })).toBeVisible()
    })

    test('only displays clients assigned to the current advisor', async ({
      page,
      advisor,
      secondAdvisor,
    }) => {
      const advisorClient = await createClient(advisor.id)
      const otherAdvisorClient = await createClient(secondAdvisor.id)
      await openFollowUpTracker(page)
      await openNew(page)

      const options = await getFollowUpForm(page)
        .getByRole('combobox', { name: /^Client/ })
        .evaluate((el) => [...el.options].map((o) => o.textContent))
      expect(options).toContain(advisorClient.name)
      expect(options).not.toContain(otherAdvisorClient.name)
    })

    test('rejects a reason containing only whitespace', async ({ page, advisor }) => {
      const client = await createClient(advisor.id)
      await openFollowUpTracker(page)
      await openNew(page)
      await fillNewFollowUp(page, {
        client,
        reason: '   ',
        stage: 'Tax Education',
        dueDate: dateOnlyFromNow(3),
      })
      await getFollowUpForm(page).getByRole('button', { name: 'Create follow-up' }).click()

      await expect(getFollowUpForm(page).getByRole('alert')).not.toBeEmpty()
      await expect(getFollowUpForm(page)).toBeVisible()
    })

    // Required fields should be rejected by the browser before submission.
    for (const missing of ['client', 'reason', 'stage', 'dueDate']) {
      test(`prevents submission when ${missing} is empty`, async ({ page, advisor }) => {
        const client = await createClient(advisor.id)
        await openFollowUpTracker(page)
        await openNew(page)

        const values = {
          client,
          reason: 'Check in',
          stage: 'Tax Education',
          dueDate: dateOnlyFromNow(3),
        }
        delete values[missing]
        await fillNewFollowUp(page, values)
        await getFollowUpForm(page).getByRole('button', { name: 'Create follow-up' }).click()

        const creationForm = getFollowUpForm(page)
        const fieldFor = {
          client: creationForm.getByRole('combobox', { name: /^Client/ }),
          reason: creationForm.getByRole('textbox', { name: 'Reason' }),
          stage: creationForm.getByRole('combobox', { name: /^Planning stage/ }),
          dueDate: creationForm.getByLabel('Due date', { exact: true }),
        }
        expect(await fieldFor[missing].evaluate((el) => el.validity.valid)).toBe(false)
        await expect(creationForm).toBeVisible()
      })
    }
  })
  //  Editing follow-ups
  test.describe('edit', () => {
    test('loads existing information and saves an updated reason', async ({ page, advisor }) => {
      const client = await createClient(advisor.id)
      const followUp = await createFollowUp(advisor.id, client.id, {
        ...FOLLOW_UP.upcoming,
        reason: 'Old reason',
        stage: 'Tax Education',
      })
      await openFollowUpTracker(page)

      await getClientRow(page, client).getByRole('button', { name: 'Edit' }).click()
      const editForm = getFollowUpForm(page, 'Edit follow-up')
      await expect(editForm).toBeVisible()
      await expect(editForm.getByRole('textbox', { name: 'Reason' })).toHaveValue('Old reason')
      await expect(editForm.getByRole('combobox', { name: /^Planning stage/ })).toHaveValue(
        'Tax Education',
      )
      await expect(editForm.getByLabel('Due date', { exact: true })).toHaveValue(
        FOLLOW_UP.upcoming.dueDate,
      )
      await editForm.getByRole('textbox', { name: 'Reason' }).fill('New reason')
      const saved = waitForFollowUpUpdate(page, followUp.id)
      await editForm.getByRole('button', { name: 'Save changes' }).click()
      await saved
      await expect(editForm).toBeHidden()
      await expect(getClientRow(page, client)).toContainText('New reason')

      await page.reload()
      await expect(getClientRow(page, client)).toContainText('New reason')
    })
  })

  test.describe('editing in the table', () => {
    test('stage change is saved', async ({ page, advisor }) => {
      const client = await createClient(advisor.id)
      const followUp = await createFollowUp(advisor.id, client.id, FOLLOW_UP.upcoming)
      await openFollowUpTracker(page)

      const select = () =>
        getClientRow(page, client).getByRole('combobox', {
          name: `Planning stage for ${client.name}`,
        })
      const saved = waitForFollowUpUpdate(page, followUp.id)
      await select().selectOption('Tax Education')
      await saved

      await page.reload()
      await expect(select()).toHaveValue('Tax Education')
    })

    test('due date change moves the row to the right filter and updates counts', async ({
      page,
      advisor,
    }) => {
      const client = await createClient(advisor.id)
      const followUp = await createFollowUp(advisor.id, client.id, FOLLOW_UP.upcoming)
      await openFollowUpTracker(page)
      await expectSummaryCounts(page, { overdue: 0, today: 0, upcoming: 1 })

      const newDate = dateOnlyFromNow(-2)
      const saved = waitForFollowUpUpdate(page, followUp.id)
      await getClientRow(page, client).getByLabel(`Due date for ${client.name}`).fill(newDate)
      await saved

      await expectSummaryCounts(page, { overdue: 1, today: 0, upcoming: 0 })
      await getFilterTab(page, 'Overdue').click()
      await expect(getClientRow(page, client)).toBeVisible()

      await page.reload()
      await expect(
        getClientRow(page, client).getByLabel(`Due date for ${client.name}`),
      ).toHaveValue(newDate)
    })

    test('saves a priority change', async ({ page, advisor }) => {
      const client = await createClient(advisor.id)
      const followUp = await createFollowUp(advisor.id, client.id, FOLLOW_UP.upcoming)
      await openFollowUpTracker(page)

      const select = () =>
        getClientRow(page, client).getByRole('combobox', { name: `Priority for ${client.name}` })
      const saved = waitForFollowUpUpdate(page, followUp.id)
      await select().selectOption('High')
      await saved

      await page.reload()
      await expect(select()).toHaveValue('High')
    })

    test('completing an overdue follow-up decreases the Overdue count', async ({
      page,
      advisor,
    }) => {
      const client = await createClient(advisor.id)
      const followUp = await createFollowUp(advisor.id, client.id, FOLLOW_UP.overdue)
      await openFollowUpTracker(page)
      await expectSummaryCounts(page, { overdue: 1, today: 0, upcoming: 0 })

      const select = () =>
        getClientRow(page, client).getByRole('combobox', { name: `Status for ${client.name}` })
      const saved = waitForFollowUpUpdate(page, followUp.id)
      await select().selectOption('Completed')
      await saved
      await expectSummaryCounts(page, { overdue: 0, today: 0, upcoming: 0 })

      await page.reload()
      await expect(select()).toHaveValue('Completed')
      await expectSummaryCounts(page, { overdue: 0, today: 0, upcoming: 0 })
    })
  })

  test.describe('summary cards and filters', () => {
    let clientByPreset

    test.beforeEach(async ({ advisor }) => {
      clientByPreset = {}
      for (const preset of Object.keys(FOLLOW_UP)) {
        const client = await createClient(advisor.id)
        await createFollowUp(advisor.id, client.id, FOLLOW_UP[preset])
        clientByPreset[preset] = client
      }
    })

    test('summary totals exclude completed and cancelled records', async ({ page }) => {
      await openFollowUpTracker(page)
      await expectSummaryCounts(page, { overdue: 1, today: 1, upcoming: 1 })
    })

    const expectedRows = {
      All: ['overdue', 'today', 'upcoming', 'completedOverdue', 'cancelledUpcoming'],
      Overdue: ['overdue'],
      'Due Today': ['today'],
      Upcoming: ['upcoming'],
    }

    for (const [tab, presets] of Object.entries(expectedRows)) {
      test(`the ${tab} tab shows exactly the expected rows`, async ({ page }) => {
        await openFollowUpTracker(page)
        await getFilterTab(page, tab).click()

        await expect(getFollowUpRows(page)).toHaveCount(presets.length)
        for (const preset of presets) {
          await expect(getClientRow(page, clientByPreset[preset])).toBeVisible()
        }
      })
    }
  })

  test('displays an empty message when a filter has no matching records', async ({
    page,
    advisor,
  }) => {
    const client = await createClient(advisor.id)
    await createFollowUp(advisor.id, client.id, FOLLOW_UP.upcoming)
    await openFollowUpTracker(page)

    await getFilterTab(page, 'Overdue').click()
    await expect(page.getByText(MESSAGES.empty)).toBeVisible()
  })

  test.describe('search', () => {
    let firstClient
    let secondClient

    test.beforeEach(async ({ advisor }) => {
      firstClient = await createClient(advisor.id)
      secondClient = await createClient(advisor.id)
      await createFollowUp(advisor.id, firstClient.id, {
        ...FOLLOW_UP.overdue,
        reason: 'Discuss RRSP top-up',
        stage: 'Tax Education',
      })
      await createFollowUp(advisor.id, secondClient.id, {
        ...FOLLOW_UP.upcoming,
        reason: 'Insurance renewal',
        stage: 'Insurance Education',
      })
    })

    for (const [by, term] of [
      ['client name', () => firstClient.name.slice(-8)],
      ['reason', () => 'RRSP'],
      ['stage', () => 'tax educ'],
    ]) {
      test(`search by ${by} keeps only matching rows`, async ({ page }) => {
        await openFollowUpTracker(page)
        await search(page).fill(term())
        await expect(getClientRow(page, firstClient)).toBeVisible()
        await expect(getClientRow(page, secondClient)).toHaveCount(0)
      })
    }

    test('combines the search term with a selected filter', async ({ page }) => {
      await openFollowUpTracker(page)
      await search(page).fill('E2E Client') // matches both clients
      await getFilterTab(page, 'Upcoming').click()
      await expect(getFollowUpRows(page)).toHaveCount(1)
      await expect(getClientRow(page, secondClient)).toBeVisible()
    })
  })
  //  Email and discussion notes

  test.describe('email composer and discussion notes', () => {
    test('copies the contact email and saves discussion notes', async ({ page, advisor }) => {
      const client = await createClient(advisor.id)
      const followUp = await createFollowUp(advisor.id, client.id, {
        ...FOLLOW_UP.upcoming,
        reason: 'Annual review',
      })
      await openFollowUpTracker(page)

      await getClientRow(page, client)
        .getByRole('button', { name: `Contact info for ${client.name}` })
        .click()
      const emailDialog = page.getByRole('dialog', { name: 'Send follow-up email' })
      await expect(emailDialog).toBeVisible()
      await expect(emailDialog.getByRole('textbox', { name: 'Subject' })).toHaveValue(
        'Follow-up: Annual review',
      )

      await emailDialog.getByRole('button', { name: 'Copy' }).click()
      await expect(emailDialog.getByText(MESSAGES.emailCopied)).toBeVisible()
      expect(await page.evaluate(() => navigator.clipboard.readText())).toBe(client.email)

      await emailDialog
        .getByRole('textbox', { name: 'Discussion notes' })
        .fill('Client agreed to meet next week.')
      await emailDialog.getByRole('button', { name: 'Save discussion' }).click()
      await expect(emailDialog.getByText(MESSAGES.notesSaved)).toBeVisible()
      await expect(emailDialog).toBeHidden()

      const res = await page.request.get(`${API_URL}/follow-ups/${followUp.id}`)
      await expect(res).toBeOK()
      expect((await res.json()).discussion_notes).toBe('Client agreed to meet next week.')

      await page.reload()
      await getClientRow(page, client)
        .getByRole('button', { name: `Contact info for ${client.name}` })
        .click()
      await expect(
        page
          .getByRole('dialog', { name: 'Send follow-up email' })
          .getByRole('textbox', { name: 'Discussion notes' }),
      ).toHaveValue('Client agreed to meet next week.')
    })
  })

  test.describe('advisor isolation', () => {
    test("prevents advisors from viewing another advisor's follow-ups", async ({
      page,
      advisor,
      secondAdvisor,
    }) => {
      const client = await createClient(advisor.id)
      await createFollowUp(advisor.id, client.id, FOLLOW_UP.upcoming)
      await openFollowUpTracker(page)
      await expect(getClientRow(page, client)).toBeVisible()

      await openFollowUpTracker(secondAdvisor.page)
      await expect(secondAdvisor.page.getByText(MESSAGES.empty)).toBeVisible()
      await expect(getClientRow(secondAdvisor.page, client)).toHaveCount(0)
    })

    test("rejects a POST request containing another advisor's client", async ({
      advisor,
      secondAdvisor,
    }) => {
      const client = await createClient(advisor.id)
      const res = await secondAdvisor.context.request.post(`${API_URL}/follow-ups`, {
        headers: { Origin: 'http://localhost:5173' },
        data: {
          client_id: Number(client.id),
          reason: 'Should not work',
          financial_planning_stage: 'Tax Education',
          due_date: dateOnlyFromNow(3),
        },
      })
      expect(res.status()).toBe(404)
      expect((await res.json()).detail).toBe(MESSAGES.unauthorizedClient)
    })
  })
})
