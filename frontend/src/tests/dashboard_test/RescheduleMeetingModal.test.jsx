import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import '@testing-library/jest-dom/vitest'
import RescheduleMeetingModal from '../../components/dashboard/RescheduleMeetingModal'
import { rescheduleMeeting } from '../../services/MeetingApi'

vi.mock('../../services/MeetingApi', () => ({
  rescheduleMeeting: vi.fn(),
}))

const meeting = {
  id: 42,
  clientName: 'Sarah Smith',
  time: '2030-06-01T09:00:00',
  completionStatus: 'Scheduled',
}

const futureDate = new Date()
futureDate.setDate(futureDate.getDate() + 7)
futureDate.setHours(0, 0, 0, 0)

const formatDate = (date) =>
  `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`

const setup = () => {
  const onClose = vi.fn()
  const onSuccess = vi.fn().mockResolvedValue(undefined)

  render(<RescheduleMeetingModal meeting={meeting} onClose={onClose} onSuccess={onSuccess} />)

  return { onClose, onSuccess }
}

const selectFutureDateAndTime = () => {
  const dateCell = document.querySelector(`[data-day="${formatDate(futureDate)}"]`)

  expect(dateCell).not.toBeNull()

  fireEvent.click(dateCell.querySelector('button'))

  fireEvent.change(screen.getByLabelText('New start time'), {
    target: { value: '14:30' },
  })
}

beforeEach(() => {
  vi.clearAllMocks()
})

afterEach(() => {
  cleanup()
})

describe('RescheduleMeetingModal', () => {
  it('renders the modal with the meeting details', () => {
    setup()

    expect(screen.getByRole('dialog')).toBeInTheDocument()
    expect(screen.getByText(/with Sarah Smith/)).toBeInTheDocument()
    expect(screen.getByLabelText('New start time')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Confirm Reschedule' })).toBeDisabled()
  })

  it('successfully reschedules and refreshes the dashboard', async () => {
    rescheduleMeeting.mockResolvedValue({
      id: 42,
      meeting_date: futureDate.toISOString(),
    })

    const { onClose, onSuccess } = setup()

    selectFutureDateAndTime()

    fireEvent.click(screen.getByRole('button', { name: 'Confirm Reschedule' }))

    await waitFor(() => {
      expect(rescheduleMeeting).toHaveBeenCalledOnce()
    })

    const [meetingId, newStart] = rescheduleMeeting.mock.calls[0]

    expect(meetingId).toBe(42)
    expect(new Date(newStart).getTime()).toBeGreaterThan(Date.now())
    expect(new Date(newStart).getHours()).toBe(14)
    expect(new Date(newStart).getMinutes()).toBe(30)

    await waitFor(() => {
      expect(onSuccess).toHaveBeenCalledOnce()
      expect(onClose).toHaveBeenCalledOnce()
    })
  })

  it('displays a scheduling conflict and keeps the modal open', async () => {
    const conflict = new Error('This time slot conflicts with another meeting.')
    conflict.status = 409
    rescheduleMeeting.mockRejectedValue(conflict)

    const { onClose, onSuccess } = setup()

    selectFutureDateAndTime()

    fireEvent.click(screen.getByRole('button', { name: 'Confirm Reschedule' }))

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'This time slot conflicts with another meeting.',
    )

    expect(screen.getByRole('dialog')).toBeInTheDocument()
    expect(onClose).not.toHaveBeenCalled()
    expect(onSuccess).not.toHaveBeenCalled()
  })

  it('prevents submission when no date or time is selected', () => {
    setup()

    expect(screen.getByRole('button', { name: 'Confirm Reschedule' })).toBeDisabled()

    expect(rescheduleMeeting).not.toHaveBeenCalled()
  })

  it('displays API errors without closing the modal', async () => {
    rescheduleMeeting.mockRejectedValue(new Error('Server unavailable'))

    const { onClose } = setup()

    selectFutureDateAndTime()

    fireEvent.click(screen.getByRole('button', { name: 'Confirm Reschedule' }))

    expect(await screen.findByRole('alert')).toHaveTextContent('Server unavailable')

    expect(onClose).not.toHaveBeenCalled()
  })
})
