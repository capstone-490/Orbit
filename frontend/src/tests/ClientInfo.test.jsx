// @vitest-environment jsdom
import { cleanup, fireEvent, render, screen, within } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import '@testing-library/jest-dom/vitest'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import ClientInfo from '../pages/ClientInfo'
import { API_BASE_URL } from '../services/AuthApi'

const client = {
  id: 1,
  name: 'Alice Smith',
  email: 'alice@example.com',
  phone_number: '514-555-1111',
  address: '100 Example Avenue',
  age: 42,
  occupation: 'Teacher',
  timeline: 'Financial Needs Analysis',
}

const response = (body, ok = true, status = 200) => ({
  ok,
  status,
  json: vi.fn().mockResolvedValue(body),
})

function renderClientInfo(path = '/clients/1') {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <Routes>
        <Route path="/clients/:clientId" element={<ClientInfo />} />
      </Routes>
    </MemoryRouter>,
  )
}

beforeEach(() => {
  vi.stubGlobal('fetch', vi.fn())
})

afterEach(() => {
  cleanup()
  vi.unstubAllGlobals()
})

describe('Client information page', () => {
  it('loads the selected client profile', async () => {
    fetch.mockResolvedValueOnce(response(client))
    renderClientInfo('/clients/1')

    expect(await screen.findByRole('heading', { name: 'Alice Smith' })).toBeInTheDocument()
    expect(screen.getByText('alice@example.com')).toBeInTheDocument()
    expect(screen.getByText('514-555-1111')).toBeInTheDocument()
    expect(screen.getByText('100 Example Avenue')).toBeInTheDocument()
    expect(screen.getByText('42 years')).toBeInTheDocument()
    expect(screen.getByText('Teacher')).toBeInTheDocument()
    expect(screen.getByText('Financial Needs Analysis')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /back to clients/i })).toHaveAttribute(
      'href',
      '/clients',
    )
    expect(fetch).toHaveBeenCalledWith(`${API_BASE_URL}/clients/1`, { credentials: 'include' })
  })

  it('shows an explicit message when the client does not exist', async () => {
    fetch.mockResolvedValueOnce(response({ detail: 'Client not found' }, false, 404))
    renderClientInfo('/clients/999')

    expect(await screen.findByRole('alert')).toHaveTextContent('Client not found.')
    expect(screen.getByRole('link', { name: /back to clients/i })).toBeInTheDocument()
  })

  it('shows a general message when the client request fails', async () => {
    fetch.mockResolvedValueOnce(response({}, false, 500))
    renderClientInfo()

    expect(await screen.findByRole('alert')).toHaveTextContent('Unable to load client information.')
  })

  it('shows the request error when fetching the client rejects', async () => {
    fetch.mockRejectedValueOnce(new Error('Network unavailable'))
    renderClientInfo()

    expect(await screen.findByRole('alert')).toHaveTextContent('Network unavailable')
  })

  it('shows a fallback for optional fields', async () => {
    fetch.mockResolvedValueOnce(
      response({
        ...client,
        address: null,
        age: null,
        occupation: null,
        timeline: null,
      }),
    )
    renderClientInfo()

    expect(await screen.findByRole('heading', { name: 'Alice Smith' })).toBeInTheDocument()
    expect(screen.getAllByText('Not provided')).toHaveLength(7)
  })

  it('switches between client profile sections from the menu bar', async () => {
    fetch.mockResolvedValueOnce(response(client))
    renderClientInfo()

    await screen.findByRole('heading', { name: 'Alice Smith' })

    expect(screen.getByRole('tab', { name: 'Overview' })).toHaveAttribute('aria-selected', 'true')
    fireEvent.click(screen.getByRole('tab', { name: 'Timeline' }))

    expect(screen.getByRole('tab', { name: 'Timeline' })).toHaveAttribute('aria-selected', 'true')
    expect(screen.getByRole('tabpanel')).toHaveTextContent(
      'Planning stage: Financial Needs Analysis',
    )

    fireEvent.click(screen.getByRole('tab', { name: 'Documents' }))
    expect(screen.getByRole('tabpanel')).toHaveTextContent('Documents for this client')

    fireEvent.click(screen.getByRole('tab', { name: 'Tasks' }))
    expect(screen.getByRole('tabpanel')).toHaveTextContent('Client-specific tasks')

    fireEvent.click(screen.getByRole('tab', { name: 'Meetings' }))
    expect(screen.getByRole('tabpanel')).toHaveTextContent('Meetings for this client')
  })

  it('supports arrow, Home, and End keyboard navigation between sections', async () => {
    fetch.mockResolvedValueOnce(response(client))
    renderClientInfo()
    await screen.findByRole('heading', { name: 'Alice Smith' })

    const overviewTab = screen.getByRole('tab', { name: 'Overview' })
    fireEvent.keyDown(overviewTab, { key: 'ArrowRight' })
    expect(screen.getByRole('tab', { name: 'Timeline' })).toHaveAttribute('aria-selected', 'true')

    fireEvent.keyDown(screen.getByRole('tab', { name: 'Timeline' }), { key: 'ArrowLeft' })
    expect(screen.getByRole('tab', { name: 'Overview' })).toHaveAttribute('aria-selected', 'true')

    fireEvent.keyDown(screen.getByRole('tab', { name: 'Overview' }), { key: 'End' })
    expect(screen.getByRole('tab', { name: 'Documents' })).toHaveAttribute('aria-selected', 'true')

    fireEvent.keyDown(screen.getByRole('tab', { name: 'Documents' }), { key: 'Home' })
    expect(screen.getByRole('tab', { name: 'Overview' })).toHaveAttribute('aria-selected', 'true')

    fireEvent.keyDown(screen.getByRole('tab', { name: 'Overview' }), { key: 'Enter' })
    expect(screen.getByRole('tab', { name: 'Overview' })).toHaveAttribute('aria-selected', 'true')
  })

  it('shows a fallback planning stage in the timeline', async () => {
    fetch.mockResolvedValueOnce(response({ ...client, timeline: null }))
    renderClientInfo()
    await screen.findByRole('heading', { name: 'Alice Smith' })

    fireEvent.click(screen.getByRole('tab', { name: 'Timeline' }))
    expect(screen.getByRole('tabpanel')).toHaveTextContent('Planning stage: Not provided')
  })

  it('loads and saves recurring expenses in the financial snapshot tab', async () => {
    fetch
      .mockResolvedValueOnce(response(client))
      .mockResolvedValueOnce(
        response({
          expenses: [],
          income: [],
          assets: [],
          debts: [],
          totals: {
            expenses: { weekly_total: 0, monthly_total: 0, annual_total: 0 },
            income: { weekly_total: 0, monthly_total: 0, annual_total: 0 },
            revenue: { weekly_total: 0, monthly_total: 0, annual_total: 0 },
            assets: { total: 0 },
            debts: { total: 0 },
            net_worth: 0,
          },
        }),
      )
      .mockResolvedValueOnce(
        response({
          expenses: [{ id: 5, description: 'Utilities', amount: '100.00', frequency: 'monthly' }],
          income: [],
          assets: [],
          debts: [],
          totals: {
            expenses: {
              weekly_total: '23.08',
              monthly_total: '100.00',
              annual_total: '1200.00',
            },
            income: { weekly_total: 0, monthly_total: 0, annual_total: 0 },
            revenue: { weekly_total: '-23.08', monthly_total: '-100.00', annual_total: '-1200.00' },
            assets: { total: 0 },
            debts: { total: 0 },
            net_worth: 0,
          },
        }),
      )
    renderClientInfo()
    await screen.findByRole('heading', { name: 'Alice Smith' })
    fireEvent.click(screen.getByRole('tab', { name: 'Financial Snapshot' }))

    expect(await screen.findByText('No expenses added yet.')).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Add expense' }))
    fireEvent.change(screen.getByLabelText('Expense description'), {
      target: { value: 'Utilities' },
    })
    fireEvent.change(screen.getByLabelText('Expense amount'), {
      target: { value: '100' },
    })
    fireEvent.click(screen.getByRole('button', { name: 'Save snapshot' }))

    expect(await screen.findByRole('status')).toHaveTextContent('Financial snapshot saved.')
    expect(screen.getByText('23.08')).toBeInTheDocument()
    expect(screen.getByText('1,200.00')).toBeInTheDocument()
    const [, options] = fetch.mock.calls[2]
    expect(JSON.parse(options.body)).toEqual({
      expenses: [{ description: 'Utilities', amount: 100, frequency: 'monthly' }],
      income: [],
      assets: [],
      debts: [],
    })
  })

  it('opens the shared edit form with current profile values as placeholders', async () => {
    fetch.mockResolvedValueOnce(response(client))
    renderClientInfo()
    await screen.findByRole('heading', { name: 'Alice Smith' })

    fireEvent.click(screen.getByRole('button', { name: 'Edit profile' }))

    const dialog = screen.getByRole('dialog', { name: 'Edit Client Profile' })
    expect(screen.getByLabelText('Full Name')).toHaveAttribute('placeholder', 'Alice Smith')
    expect(screen.getByLabelText('Email')).toHaveAttribute('placeholder', 'alice@example.com')
    expect(screen.getByLabelText('Phone Number')).toHaveAttribute('placeholder', '514-555-1111')
    expect(screen.getByLabelText('Address')).toHaveAttribute('placeholder', '100 Example Avenue')
    expect(within(dialog).getByText(/Current age: 42 years/)).toBeInTheDocument()
    expect(screen.getByLabelText('Annual income')).toHaveAttribute('placeholder', 'Not provided')
    expect(screen.getByLabelText('Risk tolerance')).toHaveValue('')
    expect(screen.getByLabelText('Target retirement age')).toHaveAttribute(
      'placeholder',
      'Not provided',
    )
  })

  it('patches changed profile fields and displays the saved information', async () => {
    fetch.mockResolvedValueOnce(response(client)).mockResolvedValueOnce(
      response({
        ...client,
        occupation: 'Principal',
        message: 'Client updated successfully',
      }),
    )
    renderClientInfo()
    await screen.findByRole('heading', { name: 'Alice Smith' })

    fireEvent.click(screen.getByRole('button', { name: 'Edit profile' }))
    fireEvent.change(screen.getByLabelText('Occupation'), {
      target: { value: 'Principal' },
    })
    fireEvent.click(screen.getByRole('button', { name: 'Save Changes' }))

    expect(await screen.findByText('Client profile updated successfully.')).toBeInTheDocument()
    expect(screen.getByText('Principal')).toBeInTheDocument()
    expect(fetch).toHaveBeenLastCalledWith(`${API_BASE_URL}/clients/1`, {
      method: 'PATCH',
      credentials: 'include',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ occupation: 'Principal' }),
    })
  })

  it('updates and displays optional financial summary fields', async () => {
    fetch.mockResolvedValueOnce(response(client)).mockResolvedValueOnce(
      response({
        ...client,
        annual_income: 95000,
        risk_tolerance: 'Moderate',
        target_retirement_age: 65,
        message: 'Client updated successfully',
      }),
    )
    renderClientInfo()
    await screen.findByRole('heading', { name: 'Alice Smith' })

    fireEvent.click(screen.getByRole('button', { name: 'Edit profile' }))
    fireEvent.change(screen.getByLabelText('Annual income'), {
      target: { value: '95000' },
    })
    fireEvent.change(screen.getByLabelText('Risk tolerance'), {
      target: { value: 'Moderate' },
    })
    fireEvent.change(screen.getByLabelText('Target retirement age'), {
      target: { value: '65' },
    })
    fireEvent.click(screen.getByRole('button', { name: 'Save Changes' }))

    expect(await screen.findByText('95,000')).toBeInTheDocument()
    expect(screen.getByText('Moderate')).toBeInTheDocument()
    expect(screen.getByText('65 years')).toBeInTheDocument()
    const [, options] = fetch.mock.calls[1]
    expect(JSON.parse(options.body)).toEqual({
      annual_income: 95000,
      risk_tolerance: 'Moderate',
      target_retirement_age: 65,
    })
  })

  it('updates the stored age when a new date of birth is entered', async () => {
    const birthDate = new Date()
    birthDate.setFullYear(birthDate.getFullYear() - 30)
    const dateOfBirth = [
      birthDate.getFullYear(),
      String(birthDate.getMonth() + 1).padStart(2, '0'),
      String(birthDate.getDate()).padStart(2, '0'),
    ].join('-')

    fetch
      .mockResolvedValueOnce(response(client))
      .mockResolvedValueOnce(response({ ...client, age: 30 }))
    renderClientInfo()
    await screen.findByRole('heading', { name: 'Alice Smith' })

    fireEvent.click(screen.getByRole('button', { name: 'Edit profile' }))
    fireEvent.change(screen.getByLabelText(/Date of Birth/), {
      target: { value: dateOfBirth },
    })
    fireEvent.click(screen.getByRole('button', { name: 'Save Changes' }))

    await screen.findByText('Client profile updated successfully.')
    const [, options] = fetch.mock.calls[1]
    expect(JSON.parse(options.body)).toEqual({ age: 30 })
  })

  it('does not send an update when no profile fields changed', async () => {
    fetch.mockResolvedValueOnce(response(client))
    renderClientInfo()
    await screen.findByRole('heading', { name: 'Alice Smith' })

    fireEvent.click(screen.getByRole('button', { name: 'Edit profile' }))
    fireEvent.click(screen.getByRole('button', { name: 'Save Changes' }))

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'Enter at least one profile change before saving.',
    )
    expect(fetch).toHaveBeenCalledTimes(1)
  })

  it('displays API errors and keeps the edit form open', async () => {
    fetch
      .mockResolvedValueOnce(response(client))
      .mockResolvedValueOnce(response({ detail: 'Email is already in use.' }, false, 409))
    renderClientInfo()
    await screen.findByRole('heading', { name: 'Alice Smith' })

    fireEvent.click(screen.getByRole('button', { name: 'Edit profile' }))
    fireEvent.change(screen.getByLabelText('Email'), {
      target: { value: 'other@example.com' },
    })
    fireEvent.click(screen.getByRole('button', { name: 'Save Changes' }))

    expect(await screen.findByRole('alert')).toHaveTextContent('Email is already in use.')
    expect(screen.getByRole('dialog', { name: 'Edit Client Profile' })).toBeInTheDocument()
  })
})
