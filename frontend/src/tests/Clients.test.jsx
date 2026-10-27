// @vitest-environment jsdom

import { cleanup, fireEvent, render, screen, within } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import '@testing-library/jest-dom/vitest'
import Clients from '../pages/Clients'

const alice = {
  id: 1,
  name: 'Alice Smith',
  email: 'alice@example.com',
  phone_number: '514-555-1111',
}

const bob = {
  id: 2,
  name: 'Bob Jones',
  email: 'bob@example.com',
  phone_number: '514-555-2222',
}

const response = (body, ok = true) => ({
  ok,
  json: vi.fn().mockResolvedValue(body),
})

function mockInitialClients(clients = [alice, bob]) {
  fetch.mockResolvedValueOnce(response(clients))
}

function openForm() {
  fireEvent.click(screen.getByRole('button', { name: /add client/i }))
  return screen.getByRole('dialog', { name: /add new client/i })
}

function fillRequiredFields(dialog) {
  fireEvent.change(within(dialog).getByLabelText(/full name/i), {
    target: { value: 'Charlie Brown' },
  })

  fireEvent.change(within(dialog).getByLabelText(/email/i), {
    target: { value: 'charlie@example.com' },
  })

  fireEvent.change(within(dialog).getByLabelText(/phone number/i), {
    target: { value: '514-555-3333' },
  })
}

beforeEach(() => {
  vi.stubGlobal('fetch', vi.fn())
})

afterEach(() => {
  cleanup()
  vi.unstubAllGlobals()
  vi.useRealTimers()
})

// ============================================
// US-14: CLIENT DIRECTORY
// ============================================

describe('US-14: Client directory', () => {
  it('displays synthetic values returned by the API instead of raw client data', async () => {
    const syntheticClient = {
      id: 1,
      name: 'Client a1b2c3d4e5f6',
      email: 'client-a1b2c3d4e5f6@invalid.test',
      phone_number: '+1-555-555-1234567',
    }
    mockInitialClients([syntheticClient])
    render(<Clients />)

    expect(await screen.findByText(syntheticClient.name)).toBeInTheDocument()
    expect(screen.getByText(syntheticClient.email)).toBeInTheDocument()
    expect(screen.queryByText('Alice Smith')).not.toBeInTheDocument()
    expect(screen.queryByText('alice@example.com')).not.toBeInTheDocument()
  })

  it('loads and displays client names and emails', async () => {
    mockInitialClients()
    render(<Clients />)

    expect(screen.getAllByText('Loading clients...').length).toBeGreaterThan(0)

    expect(await screen.findByText('Alice Smith')).toBeInTheDocument()
    expect(screen.getByText('alice@example.com')).toBeInTheDocument()
    expect(screen.getByText('Bob Jones')).toBeInTheDocument()
    expect(screen.getByText('All Clients (2)')).toBeInTheDocument()

    expect(fetch).toHaveBeenCalledWith('http://localhost:8001/clients')
  })

  it('shows an empty state when there are no clients', async () => {
    mockInitialClients([])
    render(<Clients />)

    expect(await screen.findByText('No clients found.')).toBeInTheDocument()
  })

  it('shows an error when the API fails', async () => {
    fetch.mockResolvedValueOnce(response({}, false))
    render(<Clients />)

    expect(await screen.findByRole('alert')).toHaveTextContent('Failed to load clients.')
    expect(screen.getByText('Unable to display clients.')).toBeInTheDocument()
  })
})

// ============================================
// US-15: SEARCH AND FILTER CLIENTS
// ============================================

describe('US-15: Search clients', () => {
  it('filters by name, ignoring case', async () => {
    mockInitialClients()
    render(<Clients />)

    await screen.findByText('Alice Smith')

    fireEvent.change(screen.getByRole('searchbox', { name: /search clients/i }), {
      target: { value: 'ALICE' },
    })

    expect(screen.getByText('Alice Smith')).toBeInTheDocument()
    expect(screen.queryByText('Bob Jones')).not.toBeInTheDocument()
  })

  it('filters by email', async () => {
    mockInitialClients()
    render(<Clients />)

    await screen.findByText('Alice Smith')

    fireEvent.change(screen.getByRole('searchbox', { name: /search clients/i }), {
      target: { value: 'bob@example.com' },
    })

    expect(screen.getByText('Bob Jones')).toBeInTheDocument()
    expect(screen.queryByText('Alice Smith')).not.toBeInTheDocument()
  })

  it('shows no matches and restores clients when search is cleared', async () => {
    mockInitialClients()
    render(<Clients />)

    await screen.findByText('Alice Smith')

    const search = screen.getByRole('searchbox', {
      name: /search clients/i,
    })

    fireEvent.change(search, { target: { value: 'nobody' } })

    expect(screen.getByText('No clients found.')).toBeInTheDocument()

    fireEvent.change(search, { target: { value: '' } })

    expect(screen.getByText('Alice Smith')).toBeInTheDocument()
    expect(screen.getByText('Bob Jones')).toBeInTheDocument()
  })
})

// ============================================
// US-16: ADD CLIENT
// ============================================

describe('US-16: Add client', () => {
  it('opens and closes the form', async () => {
    mockInitialClients([])
    render(<Clients />)

    await screen.findByText('No clients found.')

    openForm()

    fireEvent.click(screen.getByRole('button', { name: 'Cancel' }))

    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
  })

  it('requires name, email and phone before submission', async () => {
    mockInitialClients([])
    render(<Clients />)

    await screen.findByText('No clients found.')

    const dialog = openForm()

    expect(within(dialog).getByLabelText(/full name/i)).toBeRequired()
    expect(within(dialog).getByLabelText(/email/i)).toBeRequired()
    expect(within(dialog).getByLabelText(/phone number/i)).toBeRequired()

    fireEvent.click(within(dialog).getByRole('button', { name: /save client/i }))

    // Only the initial GET request should occur.
    expect(fetch).toHaveBeenCalledTimes(1)
  })

  it('creates a client and refreshes the directory', async () => {
    mockInitialClients([])

    fetch.mockResolvedValueOnce(response({ id: 3, message: 'Client created successfully' }))

    fetch.mockResolvedValueOnce(
      response([
        {
          id: 3,
          name: 'Charlie Brown',
          email: 'charlie@example.com',
          phone_number: '514-555-3333',
        },
      ]),
    )

    render(<Clients />)

    await screen.findByText('No clients found.')

    const dialog = openForm()
    fillRequiredFields(dialog)

    fireEvent.click(within(dialog).getByRole('button', { name: /save client/i }))

    expect(await screen.findByText('Charlie Brown')).toBeInTheDocument()

    expect(screen.getByText('Client saved successfully (ID: 3).')).toBeInTheDocument()

    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()

    const [, options] = fetch.mock.calls[1]

    expect(options.method).toBe('POST')

    expect(JSON.parse(options.body)).toMatchObject({
      name: 'Charlie Brown',
      email: 'charlie@example.com',
      phone_number: '514-555-3333',
      address: null,
    })

    expect(fetch).toHaveBeenCalledTimes(3)
  })

  it('displays duplicate-client errors', async () => {
    mockInitialClients([])

    fetch.mockResolvedValueOnce(
      response(
        {
          detail: 'A client with this email or phone number already exists.',
        },
        false,
      ),
    )

    render(<Clients />)

    await screen.findByText('No clients found.')

    const dialog = openForm()
    fillRequiredFields(dialog)

    fireEvent.click(within(dialog).getByRole('button', { name: /save client/i }))

    expect(await within(dialog).findByRole('alert')).toHaveTextContent('already exists')

    expect(screen.getByRole('dialog')).toBeInTheDocument()
  })

  it('displays a network error when saving fails', async () => {
    mockInitialClients([])

    fetch.mockRejectedValueOnce(new Error('Network unavailable'))

    render(<Clients />)

    await screen.findByText('No clients found.')

    const dialog = openForm()
    fillRequiredFields(dialog)

    fireEvent.click(within(dialog).getByRole('button', { name: /save client/i }))

    expect(await within(dialog).findByRole('alert')).toHaveTextContent('Network unavailable')
  })

  it('rejects invalid phone numbers before sending a request', async () => {
    mockInitialClients([])
    render(<Clients />)

    await screen.findByText('No clients found.')

    const dialog = openForm()
    fillRequiredFields(dialog)

    fireEvent.change(within(dialog).getByLabelText(/phone number/i), {
      target: { value: '12345' },
    })

    fireEvent.click(within(dialog).getByRole('button', { name: /save client/i }))

    expect(
      within(dialog).getByText(/please enter a valid canadian or us phone number/i),
    ).toBeInTheDocument()

    expect(fetch).toHaveBeenCalledTimes(1)
  })
})
