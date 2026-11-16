// Substantial AI assistance used; verified with frontend tests and production build.
import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import BookingDetailsStep from '../../components/booking/BookingDetailsStep'
import { bookMeeting } from '../../services/BookingApi'

vi.mock('../../services/BookingApi', async (importOriginal) => ({
  ...(await importOriginal()),
  bookMeeting: vi.fn(),
}))

afterEach(() => {
  cleanup()
  vi.restoreAllMocks()
})

describe('BookingDetailsStep', () => {
  beforeEach(() => {
    bookMeeting.mockReset()
  })

  const booking = {
    selectedType: 'introduction',
    selectedDate: new Date(2026, 10, 20),
    selectedTime: '09:30 AM',
    advisor: { id: 4, username: 'jsmith' },
  }

  const renderDetails = (props = {}) => {
    const callbacks = {
      onBack: vi.fn(),
      onChangeBooking: vi.fn(),
      onBookingComplete: vi.fn(),
    }

    render(<BookingDetailsStep {...booking} {...callbacks} {...props} />)
    return callbacks
  }

  const fillRequiredFields = () => {
    const details = {
      'First Name': 'Daniel',
      'Last Name': 'Foster',
      'Email Address': 'daniel@example.com',
      'Phone Number': '5035550167',
    }

    Object.entries(details).forEach(([label, value]) => {
      fireEvent.change(screen.getByLabelText(new RegExp(label, 'i')), {
        target: { value },
      })
    })
  }

  const submit = () =>
    fireEvent.click(screen.getByRole('button', { name: /Confirm & Schedule Meeting/i }))

  it('shows the booking summary', () => {
    renderDetails()

    expect(screen.getByText(/Introduction Meeting/)).toBeInTheDocument()
    expect(screen.getByText(/09:30 AM/)).toBeInTheDocument()
    expect(screen.getByText('jsmith')).toBeInTheDocument()
    expect(screen.getByText('STEP 4 OF 4')).toBeInTheDocument()
  })

  it('shows a follow-up consultation', () => {
    renderDetails({ selectedType: 'follow-up' })

    expect(screen.getByText(/Follow-up Consultation/)).toBeInTheDocument()
  })

  it('shows required contact fields', () => {
    renderDetails()

    const requiredFields = ['First Name', 'Last Name', 'Email Address', 'Phone Number']

    requiredFields.forEach((field) => {
      expect(screen.getByLabelText(new RegExp(field, 'i'))).toBeRequired()
    })
    expect(screen.getByLabelText(/Anything you'd like/i)).not.toBeRequired()
  })

  it('updates the contact information', () => {
    renderDetails()

    const fields = {
      'First Name': 'Daniel',
      'Last Name': 'Foster',
      'Email Address': 'daniel@example.com',
      'Phone Number': '5145551234',
      "Anything you'd like": 'Financial planning',
    }

    Object.entries(fields).forEach(([label, value]) => {
      const input = screen.getByLabelText(new RegExp(label, 'i'))

      fireEvent.change(input, { target: { value } })

      expect(input).toHaveValue(value)
    })
  })

  it('handles navigation buttons', () => {
    const { onBack, onChangeBooking } = renderDetails()

    fireEvent.click(screen.getByRole('button', { name: /Back to Date & Time/i }))
    fireEvent.click(screen.getByRole('button', { name: /Change/i }))

    expect(onBack).toHaveBeenCalledOnce()
    expect(onChangeBooking).toHaveBeenCalledOnce()
  })

  it('books the meeting with the chosen advisor', async () => {
    bookMeeting.mockResolvedValue({
      meeting_id: 9,
      meeting_uri: 'https://meet.google.com/abc-defg-hij',
    })
    renderDetails({ meetingName: 'Tax Education', duration: 30 })

    fillRequiredFields()
    fireEvent.change(screen.getByLabelText(/Anything you'd like/i), {
      target: { value: '  Questions about my RRSP  ' },
    })
    submit()

    expect(await screen.findByRole('dialog', { name: 'Meeting Scheduled!' })).toBeInTheDocument()
    expect(bookMeeting).toHaveBeenCalledWith(4, {
      name: 'Daniel Foster',
      email: 'daniel@example.com',
      phone_number: '5035550167',
      title: 'Tax Education',
      start: '2026-11-20T09:30:00-05:00',
      duration_minutes: 30,
      notes: 'Questions about my RRSP',
    })
    expect(screen.getByRole('link', { name: 'meet.google.com/abc-defg-hij' })).toHaveAttribute(
      'href',
      'https://meet.google.com/abc-defg-hij',
    )
  })

  it('leaves out empty notes', async () => {
    bookMeeting.mockResolvedValue({ meeting_id: 9 })
    renderDetails()

    fillRequiredFields()
    submit()

    await screen.findByRole('dialog', { name: 'Meeting Scheduled!' })
    expect(bookMeeting.mock.calls[0][1]).not.toHaveProperty('notes')
    // No Meet link in the response, so none is shown
    expect(screen.queryByRole('link')).not.toBeInTheDocument()
  })

  it('shows the error and stays on the form when booking fails', async () => {
    bookMeeting.mockRejectedValue(
      new Error("This phone number can't be used to book with this advisor."),
    )
    renderDetails()

    fillRequiredFields()
    submit()

    expect(await screen.findByRole('alert')).toHaveTextContent(
      "This phone number can't be used to book with this advisor.",
    )
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
    expect(screen.getByRole('button', { name: /Confirm & Schedule Meeting/i })).toBeEnabled()
  })

  it('disables the button while the booking is being saved', async () => {
    let finishBooking
    bookMeeting.mockReturnValue(
      new Promise((resolve) => {
        finishBooking = resolve
      }),
    )
    renderDetails()

    fillRequiredFields()
    submit()

    expect(await screen.findByRole('button', { name: /Scheduling/i })).toBeDisabled()

    finishBooking({ meeting_id: 9 })
    expect(await screen.findByRole('dialog', { name: 'Meeting Scheduled!' })).toBeInTheDocument()
  })

  it('starts over after the confirmation is closed', async () => {
    bookMeeting.mockResolvedValue({ meeting_id: 9 })
    const { onBookingComplete } = renderDetails()

    fillRequiredFields()
    submit()
    fireEvent.click(await screen.findByRole('button', { name: 'Done' }))

    expect(onBookingComplete).toHaveBeenCalledOnce()
  })

  it('handles form submission without logging client information', async () => {
    const consoleSpy = vi.spyOn(console, 'log').mockImplementation(() => {})
    bookMeeting.mockResolvedValue({ meeting_id: 9 })

    renderDetails()

    fillRequiredFields()
    submit()

    await screen.findByRole('dialog', { name: 'Meeting Scheduled!' })
    expect(consoleSpy).not.toHaveBeenCalled()
  })
})
