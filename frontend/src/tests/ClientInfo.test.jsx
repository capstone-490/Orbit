// @vitest-environment jsdom
import { cleanup, fireEvent, render, screen } from '@testing-library/react'
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
    expect(screen.getAllByText('Not provided')).toHaveLength(4)
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

  fireEvent.keyDown(overviewTab, { key: 'End' })
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


it('opens the Notes tab and loads client notes', async () => {
  fetch.mockResolvedValueOnce(response(client))
  fetch.mockResolvedValueOnce(response([]))

  renderClientInfo()

  await screen.findByRole('heading', { name: 'Alice Smith' })

  fireEvent.click(screen.getByRole('tab', { name: 'Notes' }))

  expect(screen.getByRole('tab', { name: 'Notes' })).toHaveAttribute(
    'aria-selected',
    'true',
  )

  expect(await screen.findByText('No notes yet')).toBeInTheDocument()

  expect(fetch).toHaveBeenCalledWith(
    `${API_BASE_URL}/clients/1/notes`,
    { credentials: 'include' },
  )
})

})
