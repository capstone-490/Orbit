
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import CreateAccount from '../pages/CreateAccount'
import { registerAdvisor } from '../services/AuthApi'

vi.mock('../services/AuthApi', () => ({
  registerAdvisor: vi.fn(),
}))

function renderRegistration() {
  return render(
    <MemoryRouter>
      <CreateAccount />
    </MemoryRouter>,
  )
}

function fillForm({
  username = 'Test Advisor',
  email = 'advisor@example.com',
  password = 'SecurePassword123',
  confirmPassword = password,
} = {}) {
  fireEvent.change(screen.getByLabelText(/^username$/i), {
    target: { value: username },
  })
  fireEvent.change(screen.getByLabelText(/^email$/i), {
    target: { value: email },
  })
  fireEvent.change(screen.getByLabelText(/^password$/i), {
    target: { value: password },
  })
  fireEvent.change(screen.getByLabelText(/^confirm password$/i), {
    target: { value: confirmPassword },
  })
}

function submitForm() {
  fireEvent.click(screen.getByRole('button', { name: /^create account$/i }))
}

describe('CreateAccount', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders the registration form', () => {
    renderRegistration()

    expect(
      screen.getByRole('heading', { name: /create your account/i }),
    ).toBeInTheDocument()
    expect(screen.getByLabelText(/^username$/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/^email$/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/^password$/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/^confirm password$/i)).toBeInTheDocument()
  })

  it('registers an advisor with valid details', async () => {
    registerAdvisor.mockResolvedValue({
      id: 1,
      username: 'Test Advisor',
      email: 'advisor@example.com',
    })

    renderRegistration()
    fillForm()
    submitForm()

    await waitFor(() => {
      expect(registerAdvisor).toHaveBeenCalledWith({
        username: 'Test Advisor',
        email: 'advisor@example.com',
        password: 'SecurePassword123',
      })
    })

    expect(
      await screen.findByText(/account created successfully/i),
    ).toBeInTheDocument()
  })

  it('rejects mismatched passwords', () => {
    renderRegistration()
    fillForm({ confirmPassword: 'DifferentPassword123' })
    submitForm()

    expect(screen.getByRole('alert')).toHaveTextContent(
      /passwords do not match/i,
    )
    expect(registerAdvisor).not.toHaveBeenCalled()
  })

  it('displays a duplicate email error', async () => {
    registerAdvisor.mockRejectedValue(
      new Error('An account with this email already exists.'),
    )

    renderRegistration()
    fillForm()
    submitForm()

    expect(
      await screen.findByRole('alert'),
    ).toHaveTextContent(/already exists/i)
  })

  it('toggles password visibility', () => {
    renderRegistration()

    const password = screen.getByLabelText(/^password$/i)

    expect(password).toHaveAttribute('type', 'password')

    fireEvent.click(screen.getByRole('button', { name: /^show password$/i }))

    expect(password).toHaveAttribute('type', 'text')
  })

  it('disables submission while registration is pending', async () => {
    registerAdvisor.mockReturnValue(new Promise(() => {}))

    renderRegistration()
    fillForm()
    submitForm()

    expect(
      await screen.findByRole('button', { name: /creating account/i }),
    ).toBeDisabled()
  })
})
