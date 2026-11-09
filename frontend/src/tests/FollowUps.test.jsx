import { cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import FollowUps from '../pages/FollowUps'
import {
  createFollowUp,
  getFollowUps,
  updateFollowUp,
  updateFollowUpStatus,
} from '../services/FollowUpsApi'

vi.mock('../services/FollowUpsApi', () => ({
  createFollowUp: vi.fn(),
  getFollowUps: vi.fn(),
  updateFollowUp: vi.fn(),
  updateFollowUpStatus: vi.fn(),
}))

function localDateKey(date = new Date()) {
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')
  return `${date.getFullYear()}-${month}-${day}`
}

const today = localDateKey()
const addDays = (days) => {
  const date = new Date(`${today}T12:00:00`)
  date.setDate(date.getDate() + days)
  return date.toISOString().slice(0, 10)
}
const clients = [
  { id: 1, name: 'Alice Smith', email: 'alice@example.com', phone_number: '416-555-0101' },
  { id: 2, name: 'Bob Jones', email: 'bob@example.com', phone_number: '416-555-0102' },
]
const followUps = [
  {
    id: 1,
    client_id: 1,
    reason: 'Review overdue proposal',
    financial_planning_stage: 'Financial Plan',
    due_date: addDays(-1),
    priority: 'High',
    status: 'Pending',
  },
  {
    id: 2,
    client_id: 2,
    reason: 'Send meeting summary',
    financial_planning_stage: 'Tax Education',
    due_date: today,
    priority: 'Medium',
    status: 'In Progress',
  },
  {
    id: 3,
    client_id: 1,
    reason: 'Prepare insurance options',
    financial_planning_stage: 'Insurance Education',
    due_date: addDays(4),
    priority: 'Low',
    status: 'Pending',
  },
]

function clientResponse(ok = true, data = clients) {
  return {
    ok,
    json: vi.fn().mockResolvedValue(data),
  }
}

async function renderLoaded(data = followUps) {
  getFollowUps.mockResolvedValue(data)
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue(clientResponse()))
  render(<FollowUps />)
  if (data.length > 0) {
    await screen.findByText('Review overdue proposal')
  } else {
    await screen.findByText('No follow-ups match your filters.')
  }
}

beforeEach(() => {
  vi.clearAllMocks()
})

afterEach(() => {
  cleanup()
  vi.unstubAllGlobals()
  vi.restoreAllMocks()
})

describe('FollowUps', () => {
  it('shows a loading state and then displays records with summary counts', async () => {
    let resolveFollowUps
    getFollowUps.mockReturnValue(
      new Promise((resolve) => {
        resolveFollowUps = resolve
      }),
    )
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(clientResponse()))
    render(<FollowUps />)

    expect(screen.getByRole('status')).toHaveTextContent('Loading follow-ups...')
    resolveFollowUps(followUps)

    expect(await screen.findByText('Review overdue proposal')).toBeInTheDocument()
    const summary = screen.getByRole('region', { name: 'Follow-up summary' })
    expect(within(summary).getByText('Overdue outreach').parentElement).toHaveTextContent('1')
    expect(within(summary).getByText('Due today').parentElement).toHaveTextContent('1')
    expect(within(summary).getByText('Upcoming').parentElement).toHaveTextContent('1')
  })

  it('filters records by client, reason, and stage search text', async () => {
    await renderLoaded()

    fireEvent.change(screen.getByRole('textbox', { name: 'Filter follow-ups' }), {
      target: { value: 'tax' },
    })

    expect(screen.getByText('Send meeting summary')).toBeInTheDocument()
    expect(screen.queryByText('Review overdue proposal')).not.toBeInTheDocument()
  })

  it('shows client contact information and provides a prefilled email action', async () => {
    await renderLoaded()

    fireEvent.click(screen.getAllByRole('button', { name: 'Contact info for Alice Smith' })[0])

    expect(screen.getByRole('dialog', { name: 'Send follow-up email' })).toHaveTextContent(
      'alice@example.com',
    )
    expect(screen.getByLabelText('Subject')).toHaveValue('Follow-up: Review overdue proposal')
    expect(screen.getByRole('button', { name: 'Email' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Phone' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Copy' })).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Phone' }))
    expect(screen.getByText('416-555-0101')).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Email' }))
    fireEvent.change(screen.getByLabelText('Discussion notes'), {
      target: { value: 'Discussed next steps.' },
    })
    fireEvent.click(screen.getByRole('button', { name: 'Save discussion' }))
    await waitFor(() =>
      expect(updateFollowUp).toHaveBeenCalledWith(1, {
        discussion_notes: 'Discussed next steps.',
      }),
    )
    expect(screen.getByRole('dialog', { name: 'Send follow-up email' })).toHaveTextContent(
      'Discussion notes saved.',
    )
    await waitFor(() =>
      expect(screen.queryByRole('dialog', { name: 'Send follow-up email' })).not.toBeInTheDocument(),
    )
    expect(screen.getByRole('status')).toHaveTextContent('Discussion notes saved.')

    fireEvent.click(screen.getAllByRole('button', { name: 'Edit' })[0])
    expect(screen.getByRole('region', { name: 'Client contact information' })).toHaveTextContent(
      'alice@example.com',
    )
    expect(screen.getByRole('link', { name: /416-555-0101/ })).toHaveAttribute(
      'href',
      'tel:416-555-0101',
    )
  })

  it.each([
    ['Overdue', 'Review overdue proposal', 'Send meeting summary'],
    ['Due Today', 'Send meeting summary', 'Review overdue proposal'],
    ['Upcoming', 'Prepare insurance options', 'Send meeting summary'],
  ])('filters records by %s', async (filter, visible, hidden) => {
    await renderLoaded()

    fireEvent.click(screen.getByRole('button', { name: filter }))

    expect(screen.getByText(visible)).toBeInTheDocument()
    expect(screen.queryByText(hidden)).not.toBeInTheDocument()
  })

  it('excludes cancelled follow-ups from overdue and upcoming filters and counts', async () => {
    const cancelledFollowUps = [
      { ...followUps[0], id: 4, reason: 'Cancelled overdue', status: 'Cancelled' },
      { ...followUps[2], id: 5, reason: 'Cancelled upcoming', status: 'Cancelled' },
    ]
    getFollowUps.mockResolvedValue(cancelledFollowUps)
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(clientResponse()))
    render(<FollowUps />)
    await screen.findByText('Cancelled overdue')

    const summary = screen.getByRole('region', { name: 'Follow-up summary' })
    expect(within(summary).getByText('Overdue outreach').parentElement).toHaveTextContent('0')
    expect(within(summary).getByText('Upcoming').parentElement).toHaveTextContent('0')

    fireEvent.click(screen.getByRole('button', { name: 'Overdue' }))
    expect(screen.getByText('No follow-ups match your filters.')).toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: 'Upcoming' }))
    expect(screen.getByText('No follow-ups match your filters.')).toBeInTheDocument()
  })

  it('shows empty and loading error states', async () => {
    getFollowUps.mockResolvedValue([])
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(clientResponse()))
    render(<FollowUps />)

    expect(await screen.findByText('No follow-ups match your filters.')).toBeInTheDocument()

    getFollowUps.mockRejectedValueOnce(new Error('Unable to load follow-ups.'))
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(clientResponse()))
    render(<FollowUps />)

    expect(await screen.findByRole('alert')).toHaveTextContent('Unable to load follow-ups.')
  })

  it('shows an error when clients cannot be loaded', async () => {
    getFollowUps.mockResolvedValue(followUps)
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(clientResponse(false)))
    render(<FollowUps />)

    expect(await screen.findByRole('alert')).toHaveTextContent('Unable to load advisor clients.')
  })

  it('creates a follow-up with the selected client and form values', async () => {
    await renderLoaded([])
    createFollowUp.mockResolvedValue({ id: 4 })
    getFollowUps.mockResolvedValueOnce([]).mockResolvedValueOnce([followUps[0]])

    fireEvent.click(screen.getByRole('button', { name: 'New Follow-Up' }))
    fireEvent.change(screen.getByLabelText('Client'), { target: { value: '2' } })
    fireEvent.change(screen.getByLabelText('Reason'), { target: { value: 'Call client' } })
    fireEvent.change(screen.getByLabelText('Planning stage'), {
      target: { value: 'Financial Plan' },
    })
    fireEvent.change(screen.getByLabelText('Due date'), { target: { value: today } })
    fireEvent.click(screen.getByRole('button', { name: 'Create follow-up' }))

    await waitFor(() =>
      expect(createFollowUp).toHaveBeenCalledWith({
        client_id: 2,
        reason: 'Call client',
        financial_planning_stage: 'Financial Plan',
        due_date: today,
        priority: 'Medium',
        status: 'Pending',
      }),
    )
  })

  it('edits an existing follow-up and saves the changed reason', async () => {
    await renderLoaded()
    updateFollowUp.mockResolvedValue({ ...followUps[0], reason: 'Updated reason' })
    getFollowUps.mockResolvedValueOnce(followUps).mockResolvedValueOnce(followUps)

    fireEvent.click(screen.getAllByRole('button', { name: 'Edit' })[0])
    fireEvent.change(screen.getByLabelText('Reason'), { target: { value: 'Updated reason' } })
    fireEvent.click(screen.getByRole('button', { name: 'Save changes' }))

    await waitFor(() =>
      expect(updateFollowUp).toHaveBeenCalledWith(1, {
        reason: 'Updated reason',
        financial_planning_stage: 'Financial Plan',
        due_date: addDays(-1),
        priority: 'High',
        status: 'Pending',
      }),
    )
  })

  it('updates a record status and displays the returned error', async () => {
    await renderLoaded()
    updateFollowUpStatus.mockResolvedValue({})

    fireEvent.change(screen.getAllByRole('combobox', { name: 'Status for Alice Smith' })[0], {
      target: { value: 'Completed' },
    })

    await waitFor(() => expect(updateFollowUpStatus).toHaveBeenCalledWith(1, 'Completed'))

    updateFollowUpStatus.mockRejectedValueOnce(new Error('Status update failed.'))
    fireEvent.change(screen.getAllByRole('combobox', { name: 'Status for Alice Smith' })[0], {
      target: { value: 'Cancelled' },
    })
    expect(await screen.findByRole('alert')).toHaveTextContent('Status update failed.')
  })

  it('updates a record priority from the table', async () => {
    await renderLoaded()
    updateFollowUp.mockResolvedValue({})

    const prioritySelect = screen.getAllByRole('combobox', {
      name: 'Priority for Alice Smith',
    })[0]
    fireEvent.change(prioritySelect, {
      target: { value: 'Low' },
    })

    await waitFor(() => expect(updateFollowUp).toHaveBeenCalledWith(1, { priority: 'Low' }))
    expect(prioritySelect).toHaveValue('Low')
  })

  it('displays save errors for create and prevents blank required submissions', async () => {
    await renderLoaded([])
    fireEvent.click(screen.getByRole('button', { name: 'New Follow-Up' }))
    fireEvent.click(screen.getByRole('button', { name: 'Create follow-up' }))
    expect(createFollowUp).not.toHaveBeenCalled()

    fireEvent.change(screen.getByLabelText('Client'), { target: { value: '1' } })
    fireEvent.change(screen.getByLabelText('Reason'), { target: { value: 'Call client' } })
    fireEvent.change(screen.getByLabelText('Planning stage'), {
      target: { value: 'Financial Plan' },
    })
    fireEvent.change(screen.getByLabelText('Due date'), { target: { value: today } })
    createFollowUp.mockRejectedValueOnce(new Error('Unable to create follow-up.'))
    fireEvent.click(screen.getByRole('button', { name: 'Create follow-up' }))

    expect(await screen.findByRole('alert')).toHaveTextContent('Unable to create follow-up.')
  })
})
