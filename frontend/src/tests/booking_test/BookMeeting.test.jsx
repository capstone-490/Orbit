// Substantial AI assistance used; verified with frontend tests and production build.
import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, describe, expect, it, vi } from 'vitest'
import BookMeeting from '../../pages/BookMeeting'

vi.mock('../../components/booking/DateTimeStep', () => ({
  default: ({ onBack, onContinue, meetingName, duration, backLabel = 'Back to Session Type' }) => (
    <div>
      <h2>Select Date & Time</h2>
      <p>
        {meetingName} · {duration} min consultation
      </p>
      <button type="button" onClick={onBack}>
        {backLabel}
      </button>
      <button type="button" onClick={onContinue}>
        Continue to Details
      </button>
    </div>
  ),
}))

afterEach(cleanup)

describe('BookMeeting', () => {
  const renderBookMeeting = () =>
    render(
      <MemoryRouter>
        <BookMeeting />
      </MemoryRouter>,
    )

  const goToDateTimeStep = () => {
    fireEvent.click(screen.getByRole('button', { name: /Continue to Date & Time/i }))
  }

  const goToDetailsStep = () => {
    goToDateTimeStep()
    fireEvent.click(screen.getByRole('button', { name: /Continue to Details/i }))
  }

  const goToStagePicker = () => {
    fireEvent.click(screen.getByText('Continue My Financial Sessions').closest('button'))
    fireEvent.click(screen.getByRole('button', { name: /Choose Your Next Session/i }))
  }

  it('renders the booking page and meeting type options', () => {
    renderBookMeeting()

    const expectedTexts = [
      'What would you like to book?',
      'Introduction Meeting',
      'Continue My Financial Sessions',
      'Presentation 1 · Corporate Introduction',
      'Follow-up Consultation',
    ]

    expectedTexts.forEach((text) => {
      expect(screen.getByText(text)).toBeInTheDocument()
    })
  })

  it('allows the user to select a meeting type', () => {
    renderBookMeeting()

    const followUpCard = screen.getByText('Continue My Financial Sessions').closest('button')

    fireEvent.click(followUpCard)

    expect(followUpCard).toHaveClass('selected')
  })

  it('moves from step 1 to step 2', () => {
    renderBookMeeting()
    goToDateTimeStep()

    expect(screen.getByText('Select Date & Time')).toBeInTheDocument()
    expect(screen.queryByText('What would you like to book?')).not.toBeInTheDocument()
  })

  it('returns from step 2 to step 1', () => {
    renderBookMeeting()
    goToDateTimeStep()

    fireEvent.click(screen.getByRole('button', { name: /Back to Session Type/i }))

    expect(screen.getByText('What would you like to book?')).toBeInTheDocument()
  })

  it('moves from step 2 to step 3', () => {
    renderBookMeeting()
    goToDetailsStep()

    expect(screen.getByText('Your Contact Details')).toBeInTheDocument()
  })

  it('returns from step 3 to step 2', () => {
    renderBookMeeting()
    goToDetailsStep()

    fireEvent.click(screen.getByRole('button', { name: /Back to Date & Time/i }))

    expect(screen.getByText('Select Date & Time')).toBeInTheDocument()
  })

  it('allows changing the booking from step 3', () => {
    renderBookMeeting()
    goToDetailsStep()

    fireEvent.click(screen.getByRole('button', { name: /Change/i }))

    expect(screen.getByText('Select Date & Time')).toBeInTheDocument()
  })

  it('shows the confirmation pop-up after submitting the details form', () => {
    renderBookMeeting()
    goToDetailsStep()

    fireEvent.change(screen.getByLabelText(/First Name/i), { target: { value: 'Daniel' } })
    fireEvent.change(screen.getByLabelText(/Last Name/i), { target: { value: 'Foster' } })
    fireEvent.change(screen.getByLabelText(/Email Address/i), {
      target: { value: 'daniel@example.com' },
    })
    fireEvent.click(screen.getByRole('button', { name: /Confirm & Schedule Meeting/i }))

    expect(screen.getByRole('dialog', { name: 'Meeting Scheduled!' })).toBeInTheDocument()
    expect(screen.getByText('daniel@example.com')).toBeInTheDocument()
  })

  it('starts a new booking after closing the confirmation pop-up', () => {
    renderBookMeeting()
    goToDetailsStep()

    fireEvent.change(screen.getByLabelText(/First Name/i), { target: { value: 'Daniel' } })
    fireEvent.change(screen.getByLabelText(/Last Name/i), { target: { value: 'Foster' } })
    fireEvent.change(screen.getByLabelText(/Email Address/i), {
      target: { value: 'daniel@example.com' },
    })
    fireEvent.click(screen.getByRole('button', { name: /Confirm & Schedule Meeting/i }))
    fireEvent.click(screen.getByRole('button', { name: 'Done' }))

    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
    expect(screen.getByText('What would you like to book?')).toBeInTheDocument()
  })

  describe('Continue My Financial Sessions', () => {
    it('shows the advisory stage picker instead of going straight to step 2', () => {
      renderBookMeeting()
      goToStagePicker()

      expect(screen.getByText('Continue Your Financial Journey')).toBeInTheDocument()
      expect(screen.getByText('Advisory Stage')).toBeInTheDocument()
      expect(screen.getByText('Client Details')).toBeInTheDocument()
      expect(screen.queryByText('Select Date & Time')).not.toBeInTheDocument()
    })

    it('returns from the stage picker to the session type', () => {
      renderBookMeeting()
      goToStagePicker()

      fireEvent.click(screen.getByRole('button', { name: /Back to Session Type/i }))

      expect(screen.getByText('What would you like to book?')).toBeInTheDocument()
    })

    it('carries the chosen stage into the date & time step', () => {
      renderBookMeeting()
      goToStagePicker()

      fireEvent.click(screen.getByRole('radio', { name: /Financial Needs Analysis/i }))
      fireEvent.click(screen.getByRole('button', { name: /Continue to Date & Time/i }))

      expect(screen.getByText('Select Date & Time')).toBeInTheDocument()
      expect(
        screen.getByText('Financial Needs Analysis (FNA) · 60 min consultation'),
      ).toBeInTheDocument()
    })

    it('goes back from date & time to the stage picker with the stage still selected', () => {
      renderBookMeeting()
      goToStagePicker()

      fireEvent.click(screen.getByRole('radio', { name: /Tax Education/i }))
      fireEvent.click(screen.getByRole('button', { name: /Continue to Date & Time/i }))
      fireEvent.click(screen.getByRole('button', { name: /Back to Advisory Stage/i }))

      expect(screen.getByText('Continue Your Financial Journey')).toBeInTheDocument()
      expect(screen.getByRole('radio', { name: /Tax Education/i })).toBeChecked()
    })

    it('shows the chosen stage in the booking summary', () => {
      renderBookMeeting()
      goToStagePicker()

      fireEvent.click(screen.getByRole('radio', { name: /Tax Education/i }))
      fireEvent.click(screen.getByRole('button', { name: /Continue to Date & Time/i }))
      fireEvent.click(screen.getByRole('button', { name: /Continue to Details/i }))

      expect(screen.getByText('Tax Education (45 min)')).toBeInTheDocument()
    })
  })
})
