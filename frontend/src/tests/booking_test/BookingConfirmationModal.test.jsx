// Substantial AI assistance used; verified with frontend tests and production build.
import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import BookingConfirmationModal from '../../components/booking/BookingConfirmationModal'

afterEach(cleanup)

describe('BookingConfirmationModal', () => {
  const renderModal = (onDone = vi.fn()) => {
    render(
      <BookingConfirmationModal
        meetingName="Tax Education"
        duration={45}
        formattedDate="Thu, Nov 19, 2026"
        selectedTime="10:30 AM"
        advisorName="Nayiri Saba"
        email="daniel@example.com"
        onDone={onDone}
      />,
    )
    return onDone
  }

  it('shows the booking details and the email the confirmation was sent to', () => {
    renderModal()

    expect(screen.getByRole('dialog', { name: 'Meeting Scheduled!' })).toBeInTheDocument()
    expect(screen.getByText('Tax Education (45 min)')).toBeInTheDocument()
    expect(screen.getByText('Thu, Nov 19, 2026 at 10:30 AM')).toBeInTheDocument()
    expect(screen.getByText('daniel@example.com')).toBeInTheDocument()
  })

  it('calls onDone when Done is clicked', () => {
    const onDone = renderModal()

    fireEvent.click(screen.getByRole('button', { name: 'Done' }))

    expect(onDone).toHaveBeenCalledTimes(1)
  })

  it('calls onDone when Escape is pressed', () => {
    const onDone = renderModal()

    fireEvent.keyDown(document, { key: 'Escape' })

    expect(onDone).toHaveBeenCalledTimes(1)
  })
})
