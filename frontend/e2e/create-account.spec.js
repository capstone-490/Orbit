// Substantial AI assistance used;

import { randomUUID } from 'node:crypto'
import { expect, expectCannotLogin, makeAdvisor, registerAdvisor, test } from './fixtures.js'
import { findAdvisorByEmail } from './helpers/db.js'

//  Form labels and messages
const FORM_LABELS = {
  username: 'Username',
  email: 'Email',
  password: 'Password',
  confirm: 'Confirm Password',
  submit: 'Create Account',
  goToSignIn: 'Go to Sign In',
  loginEmail: 'Email',
  loginPassword: 'Password',
  loginSubmit: 'Sign In',
}

const EXPECTED_MESSAGES = {
  accountCreated: 'Account created successfully!',
  duplicate: 'An account with this email already exists.',
  blankUsername: 'Please enter a username.',
  mismatch: 'Passwords do not match.',
}

// Page helpers

const getField = (page, label) => page.getByLabel(label, { exact: true })
const getSuccessMessage = (page) =>
  page.getByRole('heading', { name: EXPECTED_MESSAGES.accountCreated })

const fillRegistrationForm = async (
  page,
  { username, email, password, confirmPassword = password },
) => {
  await getField(page, FORM_LABELS.username).fill(username)
  await getField(page, FORM_LABELS.email).fill(email)
  await getField(page, FORM_LABELS.password).fill(password)
  await getField(page, FORM_LABELS.confirm).fill(confirmPassword)
}

const isFieldValid = (locator) => locator.evaluate((element) => element.validity.valid)

const submit = (page) => page.getByRole('button', { name: FORM_LABELS.submit, exact: true }).click()

// Account creation tests
test.describe('Create account', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/create-account')
  })

  test('successfully creates a new account', async ({ page }) => {
    const newAdvisor = makeAdvisor('signup')
    await fillRegistrationForm(page, newAdvisor)
    await submit(page)
    await expect(getSuccessMessage(page)).toBeVisible()
  })

  test('navigates to sign in and allows the new account to log in', async ({ page }) => {
    const newAdvisor = makeAdvisor('signin')
    await fillRegistrationForm(page, newAdvisor)
    await submit(page)
    await expect(getSuccessMessage(page)).toBeVisible()

    await page.getByRole('button', { name: FORM_LABELS.goToSignIn }).click()
    await expect(page).toHaveURL(/\/login$/)

    await getField(page, FORM_LABELS.loginEmail).fill(newAdvisor.email)
    await getField(page, FORM_LABELS.loginPassword).fill(newAdvisor.password)
    await page.getByRole('button', { name: FORM_LABELS.loginSubmit, exact: true }).click()
    await expect(page).toHaveURL(/\/dashboard/)
  })

  test('rejects registration when the email is already in use', async ({ page, request }) => {
    const existingAdvisor = makeAdvisor('duplicate')
    await registerAdvisor(request, existingAdvisor)

    const duplicateAdvisor = {
      ...makeAdvisor('duplicateAttempt'),
      email: existingAdvisor.email,
      password: 'Another-e2e-password-456!',
    }
    await fillRegistrationForm(page, duplicateAdvisor)
    await submit(page)

    await expect(page.getByRole('alert')).toHaveText(EXPECTED_MESSAGES.duplicate)
    await expect(getSuccessMessage(page)).toHaveCount(0)
    await expectCannotLogin(request, duplicateAdvisor.email, duplicateAdvisor.password)
  })

  test('rejects a password that is shorter than the required length', async ({ page, request }) => {
    const advisorWithShortPassword = { ...makeAdvisor('shortPassword'), password: 'Short-pw-1' } // 10 chars
    await fillRegistrationForm(page, advisorWithShortPassword)
    await submit(page)

    expect(await isFieldValid(getField(page, FORM_LABELS.password))).toBe(false)
    await expect(getSuccessMessage(page)).toHaveCount(0)
    await expectCannotLogin(
      request,
      advisorWithShortPassword.email,
      advisorWithShortPassword.password,
    )
  })

  test('an empty username is blocked by browser validation', async ({ page, request }) => {
    const advisorWithoutUsername = { ...makeAdvisor('nouser'), username: '' }
    await fillRegistrationForm(page, advisorWithoutUsername)
    await submit(page)

    expect(await isFieldValid(getField(page, FORM_LABELS.username))).toBe(false)
    await expect(getSuccessMessage(page)).toHaveCount(0)
    await expectCannotLogin(request, advisorWithoutUsername.email, advisorWithoutUsername.password)
  })

  test('a username of only spaces is rejected', async ({ page, request }) => {
    const advisorWithWhitespaceUsername = { ...makeAdvisor('spaces'), username: '   ' }
    await fillRegistrationForm(page, advisorWithWhitespaceUsername)
    await submit(page)

    await expect(page.getByRole('alert')).toHaveText(EXPECTED_MESSAGES.blankUsername)
    await expect(getSuccessMessage(page)).toHaveCount(0)
    await expectCannotLogin(
      request,
      advisorWithWhitespaceUsername.email,
      advisorWithWhitespaceUsername.password,
    )
  })

  test('mismatched passwords are rejected', async ({ page, request }) => {
    const advisor = makeAdvisor('mismatch')
    await fillRegistrationForm(page, { ...advisor, confirmPassword: `${advisor.password}x` })
    await submit(page)

    await expect(page.getByRole('alert')).toHaveText(EXPECTED_MESSAGES.mismatch)
    await expect(getSuccessMessage(page)).toHaveCount(0)
    await expectCannotLogin(request, advisor.email, advisor.password)
  })

  test('normalizes email addresses to lowercase during registration', async ({ page }) => {
    const uniqueId = randomUUID().slice(0, 8)
    const advisor = { ...makeAdvisor('case'), email: `TestUser-${uniqueId}@gmail.com` }
    await fillRegistrationForm(page, advisor)
    await submit(page)
    await expect(getSuccessMessage(page)).toBeVisible()

    const stored = await findAdvisorByEmail(advisor.email)
    expect(stored, 'advisor row should exist').toBeTruthy()
    expect(stored.email).toBe(advisor.email.toLowerCase())
  })
})
