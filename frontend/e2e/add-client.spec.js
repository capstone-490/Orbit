// Substantial AI assistance used;

import { randomUUID } from 'node:crypto'
import { expect, test } from './fixtures.js'
import { createClient, findClientByEmail, nanpPhone } from './helpers/db.js'

// Client form labels and messages

const CLIENT_FORM_LABELS = {
  addButton: '+ Add Client',
  dialogTitle: 'Add New Client',
  fullName: 'Full Name *',
  email: 'Email *',
  phoneNumber: 'Phone Number *',
  address: 'Address',
  dob: 'Date of Birth (used to calculate age)',
  occupation: 'Occupation',
  timeline: 'Timeline',
  saveButton: 'Save Client',
  cancel: 'Cancel',
  close: 'Close form',
}

const CLIENT_MESSAGES = {
  saved: /Client saved successfully \(ID: \d+\)/,
  invalidPhone: 'Please enter a valid Canadian or US phone number.',
  duplicate: 'A client with this email or phone number already exists.',
}

//  Test data helpers

// Generate a short identifier to keep test data unique.
const createUniqueId = () => randomUUID().slice(0, 8)

/**
 * Creates unique client information for a test.
 * A valid random phone number is generated unless one is provided.
 */
const buildTestClient = (overrides = {}) => {
  const uniqueId = createUniqueId()
  return {
    name: `Add Client ${uniqueId}`,
    email: `add-client-${uniqueId}@example.com`,
    phone: nanpPhone(),
    ...overrides,
  }
}

// Split a valid phone number into its area code and remaining digits.
const getPhoneNumberParts = () => nanpPhone().match(/\d+/g)

//  Page element helpers

// Locate the Add New Client dialog and its form fields.
const getClientDialog = (page) => page.getByRole('dialog', { name: CLIENT_FORM_LABELS.dialogTitle })
const getClientField = (page, label) => getClientDialog(page).getByLabel(label, { exact: true })

// Check the number of clients displayed in the client list.
const getClientCountLabel = (page, count) => page.getByText(`All Clients (${count})`)

// Form interaction helpers

// Open the client creation dialog.
async function openAddClientDialog(page) {
  await page.getByRole('button', { name: CLIENT_FORM_LABELS.addButton }).click()
  await expect(getClientDialog(page)).toBeVisible()
}

// Fill in the three mandatory client fields.
async function fillRequiredClientFields(page, client) {
  await getClientField(page, CLIENT_FORM_LABELS.fullName).fill(client.name)
  await getClientField(page, CLIENT_FORM_LABELS.email).fill(client.email)
  await getClientField(page, CLIENT_FORM_LABELS.phoneNumber).fill(client.phone)
}

// Submit the client creation form.
const saveClient = (page) =>
  getClientDialog(page)
    .getByRole('button', { name: CLIENT_FORM_LABELS.saveButton, exact: true })
    .click()

// Request tracking helpers

/**
 * Tracks POST requests sent to the /clients endpoint.
 * Used to verify that invalid submissions do not reach the backend.
 */
function trackClientCreationRequests(page) {
  const clientRequests = []
  page.on('request', (request) => {
    const isClientCreationRequest =
      request.method() === 'POST' && new URL(request.url()).pathname.endsWith('/clients')
    if (isClientCreationRequest) {
      clientRequests.push(request)
    }
  })
  return clientRequests
}

// Date and phone helpers

/**
 * Generates a date of birth for someone who turned the specified age
 * approximately two months ago, avoiding birthday boundary issues.
 */
function createDateOfBirthForAge(age) {
  const birthDate = new Date()
  birthDate.setUTCFullYear(birthDate.getUTCFullYear() - age)
  birthDate.setUTCDate(birthDate.getUTCDate() - 60)
  return birthDate.toISOString().slice(0, 10)
}

// Add Client tests
test.describe('Add Client', () => {
  test.beforeEach(async ({ page, advisor: _advisor }) => {
    await page.goto('/clients')
    await expect(page.getByRole('button', { name: CLIENT_FORM_LABELS.addButton })).toBeVisible()
  })

  //  Successful client creation
  test.describe('successful client creation', () => {
    test('creates a client using only the required fields', async ({ page, advisor }) => {
      await createClient(advisor.id)
      await page.reload()
      await expect(getClientCountLabel(page, 1)).toBeVisible()

      const newClient = buildTestClient()
      await openAddClientDialog(page)
      await fillRequiredClientFields(page, newClient)
      await saveClient(page)

      await expect(getClientDialog(page)).toBeHidden()
      await expect(page.getByRole('status')).toHaveText(CLIENT_MESSAGES.saved)
      await expect(page.getByText(newClient.name)).toBeVisible()
      await expect(page.getByText(newClient.email)).toBeVisible()
      await expect(getClientCountLabel(page, 2)).toBeVisible()
    })

    test('creates a client with all fields and calculates their age', async ({ page }) => {
      const newClient = buildTestClient()
      await openAddClientDialog(page)
      await fillRequiredClientFields(page, newClient)
      await getClientField(page, CLIENT_FORM_LABELS.address).fill('123 Main St, Montreal, QC')
      await getClientField(page, CLIENT_FORM_LABELS.dob).fill(createDateOfBirthForAge(30))
      await getClientField(page, CLIENT_FORM_LABELS.occupation).fill('Engineer')
      await getClientDialog(page)
        .getByRole('combobox', { name: /^Timeline/ })
        .selectOption({ label: 'Financial Plan' })
      await saveClient(page)
      await expect(getClientDialog(page)).toBeHidden()

      // Verify that the submitted optional information was saved correctly.
      const savedClient = await findClientByEmail(newClient.email)
      expect(savedClient).toBeTruthy()
      expect(savedClient.age).toBe(30)
      expect(savedClient.address).toBe('123 Main St, Montreal, QC')
      expect(savedClient.occupation).toBe('Engineer')
      expect(savedClient.timeline).toBe('Financial Plan')
    })

    test('stores empty optional fields as NULL instead of empty strings', async ({ page }) => {
      const newClient = buildTestClient()
      await openAddClientDialog(page)
      await fillRequiredClientFields(page, newClient)
      await saveClient(page)
      await expect(getClientDialog(page)).toBeHidden()

      const savedClient = await findClientByEmail(newClient.email)
      expect(savedClient.address).toBeNull()
      expect(savedClient.age).toBeNull()
      expect(savedClient.occupation).toBeNull()
      expect(savedClient.timeline).toBeNull()
    })

    test('keeps the newly created client in the list after reloading', async ({ page }) => {
      const newClient = buildTestClient()
      await openAddClientDialog(page)
      await fillRequiredClientFields(page, newClient)
      await saveClient(page)
      await expect(getClientDialog(page)).toBeHidden()

      await page.reload()
      await expect(page.getByText(newClient.name)).toBeVisible()
    })

    // Verify that the form accepts different valid North American phone formats.
    const validPhoneFormats = [
      [
        '(416) 555-0123 style',
        ([areaCode, exchangeCode, subscriberNumber]) =>
          `(${areaCode}) ${exchangeCode}-${subscriberNumber}`,
      ],
      [
        '+1 416-555-0123 style',
        ([areaCode, exchangeCode, subscriberNumber]) =>
          `+1 ${areaCode}-${exchangeCode}-${subscriberNumber}`,
      ],
    ]
    for (const [formatDescription, formatPhoneNumber] of validPhoneFormats) {
      test(`accepts phone numbers in ${formatDescription}`, async ({ page }) => {
        const newClient = buildTestClient({ phone: formatPhoneNumber(getPhoneNumberParts()) })
        await openAddClientDialog(page)
        await fillRequiredClientFields(page, newClient)
        await saveClient(page)

        await expect(getClientDialog(page)).toBeHidden()
        await expect(page.getByText(newClient.name)).toBeVisible()
      })
    }
  })

  // Form validation and error handling
  test.describe('validation and errors', () => {
    const invalidPhoneNumbers = ['123', '555-0123', '(016) 555-0123', '(116) 555-0123']
    for (const invalidPhone of invalidPhoneNumbers) {
      test(`rejects invalid phone "${invalidPhone}" without sending a request`, async ({
        page,
      }) => {
        const clientRequests = trackClientCreationRequests(page)
        const newClient = buildTestClient({ phone: invalidPhone })
        await openAddClientDialog(page)
        await fillRequiredClientFields(page, newClient)
        await saveClient(page)

        await expect(getClientDialog(page).getByText(CLIENT_MESSAGES.invalidPhone)).toBeVisible()
        await expect(getClientDialog(page)).toBeVisible()
        expect(clientRequests).toHaveLength(0)
      })
    }

    test('prevents submission when a required field is empty', async ({ page }) => {
      const clientRequests = trackClientCreationRequests(page)
      const newClient = buildTestClient()
      await openAddClientDialog(page)

      // Leave the name empty while filling in the other required fields.
      await getClientField(page, CLIENT_FORM_LABELS.email).fill(newClient.email)
      await getClientField(page, CLIENT_FORM_LABELS.phoneNumber).fill(newClient.phone)
      await saveClient(page)

      const nameField = getClientField(page, CLIENT_FORM_LABELS.fullName)
      expect(await nameField.evaluate((element) => element.validity.valid)).toBe(false)
      await expect(getClientDialog(page)).toBeVisible()
      expect(clientRequests).toHaveLength(0)
      expect(await findClientByEmail(newClient.email)).toBeUndefined()
    })

    test('displays an error when an existing email is used', async ({ page, advisor }) => {
      const existingClient = await createClient(advisor.id)
      await openAddClientDialog(page)
      await fillRequiredClientFields(page, buildTestClient({ email: existingClient.email }))
      await saveClient(page)

      await expect(getClientDialog(page).getByText(CLIENT_MESSAGES.duplicate)).toBeVisible()
      await expect(getClientDialog(page)).toBeVisible()
    })

    test('displays an error when an existing phone number is used', async ({ page }) => {
      // Create the first client through the UI to use the backend's normalized phone number format.
      const firstClient = buildTestClient()
      await openAddClientDialog(page)
      await fillRequiredClientFields(page, firstClient)
      await saveClient(page)
      await expect(getClientDialog(page)).toBeHidden()

      // Attempt to register another client with the same phone number.
      const duplicateClient = buildTestClient({
        phone: firstClient.phone,
      })
      await openAddClientDialog(page)
      await fillRequiredClientFields(page, duplicateClient)
      await saveClient(page)

      await expect(getClientDialog(page).getByText(CLIENT_MESSAGES.duplicate)).toBeVisible()
    })
  })

  //  Dialog closing and reopening behaviour
  test.describe('modal behaviour', () => {
    // Different ways a user can close the Add Client dialog.
    const dialogCloseActions = {
      Cancel: (page) =>
        getClientDialog(page).getByRole('button', { name: CLIENT_FORM_LABELS.cancel }).click(),
      'Close button': (page) =>
        getClientDialog(page).getByRole('button', { name: CLIENT_FORM_LABELS.close }).click(),
      'backdrop click': (page) =>
        page
          .getByRole('button', { name: 'Close Add Client form' })
          .click({ position: { x: 5, y: 5 } }),
    }

    for (const [closeMethod, closeDialog] of Object.entries(dialogCloseActions)) {
      test(`${closeMethod} closes the dialog without creating a client`, async ({ page }) => {
        const clientRequests = trackClientCreationRequests(page)
        const newClient = buildTestClient()
        await openAddClientDialog(page)
        await fillRequiredClientFields(page, newClient)
        await closeDialog(page)

        await expect(getClientDialog(page)).toBeHidden()
        expect(clientRequests).toHaveLength(0)
        expect(await findClientByEmail(newClient.email)).toBeUndefined()
      })
    }

    test('clears previous validation errors when the dialog is reopened', async ({ page }) => {
      await openAddClientDialog(page)
      await fillRequiredClientFields(page, buildTestClient({ phone: '123' }))
      await saveClient(page)
      await expect(getClientDialog(page).getByText(CLIENT_MESSAGES.invalidPhone)).toBeVisible()

      // Close and reopen the form to verify that the previous error is cleared.
      await getClientDialog(page).getByRole('button', { name: CLIENT_FORM_LABELS.cancel }).click()
      await openAddClientDialog(page)
      await expect(getClientDialog(page).getByText(CLIENT_MESSAGES.invalidPhone)).toHaveCount(0)
    })
  })

  //  Client search and advisor isolation
  test.describe('search and isolation', () => {
    test('filters the client list by partial name or email', async ({ page, advisor }) => {
      const otherClient = await createClient(advisor.id)
      const newClient = buildTestClient()
      await page.reload()
      await openAddClientDialog(page)
      await fillRequiredClientFields(page, newClient)
      await saveClient(page)
      await expect(getClientDialog(page)).toBeHidden()

      const clientSearch = page.getByRole('searchbox', { name: 'Search clients' })
      // Search using the unique portion of the client's name.
      await clientSearch.fill(newClient.name.slice(-8))
      await expect(page.getByText(newClient.name)).toBeVisible()
      await expect(page.getByText(otherClient.name)).toHaveCount(0)

      await clientSearch.fill(newClient.email.split('@')[0])
      await expect(page.getByText(newClient.email)).toBeVisible()
      await expect(page.getByText(otherClient.email)).toHaveCount(0)
    })

    test("does not display one advisor's clients to another advisor", async ({
      page,
      secondAdvisor,
    }) => {
      const newClient = buildTestClient()
      await openAddClientDialog(page)
      await fillRequiredClientFields(page, newClient)
      await saveClient(page)
      await expect(page.getByText(newClient.name)).toBeVisible()

      // Check the client list using a different advisor's session.
      await secondAdvisor.page.goto('/clients')
      await expect(getClientCountLabel(secondAdvisor.page, 0)).toBeVisible()
      await expect(secondAdvisor.page.getByText(newClient.name)).toHaveCount(0)
    })
  })
})
