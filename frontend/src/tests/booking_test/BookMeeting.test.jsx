// Substantial AI assistance used; verified with frontend tests and production build.
import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import BookMeeting from '../../pages/BookMeeting'
import { bookMeeting, getBookableAdvisors } from '../../services/BookingApi'

vi.mock('../../services/BookingApi', async (importOriginal) => ({
  ...(await importOriginal()),
  getBookableAdvisors: vi.fn(),
  bookMeeting: vi.fn(),
}))

vi.mock('../../components/booking/DateTimeStep', () => ({
  default: ({
    onBack,
    onContinue,
    setSelectedDate,
    setSelectedTime,
    meetingName,
    duration,
    backLabel = 'Back to Session Type',
  }) => (
    <div>
      <h2>Select Date & Time</h2>
      <p>
        {meetingName} · {duration} min consultation
      </p>
      <button type="button" onClick={onBack}>
        {backLabel}
      </button>
      <button
        type="button"
        onClick={() => {
          // Picks a slot, like a client would, before continuing
          setSelectedDate(new Date(2026, 10, 19))
          setSelectedTime('10:30 AM')
          onContinue()
        }}
      >
        Continue to Details
      </button>
    </div>
  ),
}))

afterEach(cleanup)

describe('BookMeeting', () => {
  beforeEach(() => {
    getBookableAdvisors.mockReset().mockResolvedValue([
      { id: 1, username: 'nsaba' },
      { id: 4, username: 'jsmith' },
    ])
    bookMeeting.mockReset().mockResolvedValue({ meeting_id: 9 })
  })

  // Renders the page and picks an advisor, ending on the session type step
  const renderBookMeeting = async () => {
    render(
      <MemoryRouter>
        <BookMeeting />
      </MemoryRouter>,
    )

    fireEvent.click(await screen.findByRole('radio', { name: /jsmith/ }))
    fireEvent.click(screen.getByRole('button', { name: /Continue to Session Type/i }))
  }

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

  const fillDetails = () => {
    fireEvent.change(screen.getByLabelText(/First Name/i), { target: { value: 'Daniel' } })
    fireEvent.change(screen.getByLabelText(/Last Name/i), { target: { value: 'Foster' } })
    fireEvent.change(screen.getByLabelText(/Email Address/i), {
      target: { value: 'daniel@example.com' },
    })
    fireEvent.change(screen.getByLabelText(/Phone Number/i), {
      target: { value: '5035550167' },
    })
  }

  it('starts by asking the client to choose an advisor', async () => {
    render(
      <MemoryRouter>
        <BookMeeting />
      </MemoryRouter>,
    )

    expect(await screen.findByText('Who would you like to meet with?')).toBeInTheDocument()
    expect(screen.getByRole('radio', { name: /nsaba/ })).toBeInTheDocument()
    expect(screen.getByText('STEP 1').nextElementSibling).toHaveTextContent('Advisor')
    expect(screen.queryByText('What would you like to book?')).not.toBeInTheDocument()
  })

  it('returns from the session type to the advisor with it still selected', async () => {
    await renderBookMeeting()

    fireEvent.click(screen.getByRole('button', { name: /Back to Advisor/i }))

    expect(await screen.findByRole('radio', { name: /jsmith/ })).toBeChecked()
  })

  it('renders the booking page and meeting type options', async () => {
    await renderBookMeeting()

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

  it('allows the user to select a meeting type', async () => {
    await renderBookMeeting()

    const followUpCard = screen.getByText('Continue My Financial Sessions').closest('button')

    fireEvent.click(followUpCard)

    expect(followUpCard).toHaveClass('selected')
  })

  it('moves from the session type to date & time', async () => {
    await renderBookMeeting()
    goToDateTimeStep()

    expect(screen.getByText('Select Date & Time')).toBeInTheDocument()
    expect(screen.queryByText('What would you like to book?')).not.toBeInTheDocument()
  })

  it('returns from date & time to the session type', async () => {
    await renderBookMeeting()
    goToDateTimeStep()

    fireEvent.click(screen.getByRole('button', { name: /Back to Session Type/i }))

    expect(screen.getByText('What would you like to book?')).toBeInTheDocument()
  })

  it('moves from date & time to the details', async () => {
    await renderBookMeeting()
    goToDetailsStep()

    expect(screen.getByText('Your Contact Details')).toBeInTheDocument()
    // The summary shows the advisor chosen in the first step
    expect(screen.getByText('jsmith')).toBeInTheDocument()
  })

  it('returns from the details to date & time', async () => {
    await renderBookMeeting()
    goToDetailsStep()

    fireEvent.click(screen.getByRole('button', { name: /Back to Date & Time/i }))

    expect(screen.getByText('Select Date & Time')).toBeInTheDocument()
  })

  it('allows changing the booking from the details', async () => {
    await renderBookMeeting()
    goToDetailsStep()

    fireEvent.click(screen.getByRole('button', { name: /Change/i }))

    expect(screen.getByText('Select Date & Time')).toBeInTheDocument()
  })

  it('books with the chosen advisor and shows the confirmation pop-up', async () => {
    await renderBookMeeting()
    goToDetailsStep()

    fillDetails()
    fireEvent.click(screen.getByRole('button', { name: /Confirm & Schedule Meeting/i }))

    expect(await screen.findByRole('dialog', { name: 'Meeting Scheduled!' })).toBeInTheDocument()
    expect(screen.getByText('daniel@example.com')).toBeInTheDocument()
    expect(bookMeeting).toHaveBeenCalledWith(
      4,
      expect.objectContaining({
        title: 'Introduction Meeting',
        start: '2026-11-19T10:30:00-05:00',
        duration_minutes: 45,
      }),
    )
  })

  it('starts a new booking after closing the confirmation pop-up', async () => {
    await renderBookMeeting()
    goToDetailsStep()

    fillDetails()
    fireEvent.click(screen.getByRole('button', { name: /Confirm & Schedule Meeting/i }))
    fireEvent.click(await screen.findByRole('button', { name: 'Done' }))

    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
    expect(await screen.findByText('Who would you like to meet with?')).toBeInTheDocument()
    expect(await screen.findByRole('radio', { name: /jsmith/ })).not.toBeChecked()
  })

  describe('Continue My Financial Sessions', () => {
    it('shows the advisory stage picker instead of going straight to date & time', async () => {
      await renderBookMeeting()
      goToStagePicker()

      expect(screen.getByText('Continue Your Financial Journey')).toBeInTheDocument()
      expect(screen.getByText('Advisory Stage')).toBeInTheDocument()
      expect(screen.getByText('Client Details')).toBeInTheDocument()
      expect(screen.queryByText('Select Date & Time')).not.toBeInTheDocument()
    })

    it('returns from the stage picker to the session type', async () => {
      await renderBookMeeting()
      goToStagePicker()

      fireEvent.click(screen.getByRole('button', { name: /Back to Session Type/i }))

      expect(screen.getByText('What would you like to book?')).toBeInTheDocument()
    })

    it('carries the chosen stage into the date & time step', async () => {
      await renderBookMeeting()
      goToStagePicker()

      fireEvent.click(screen.getByRole('radio', { name: /Financial Needs Analysis/i }))
      fireEvent.click(screen.getByRole('button', { name: /Continue to Date & Time/i }))

      expect(screen.getByText('Select Date & Time')).toBeInTheDocument()
      expect(
        screen.getByText('Financial Needs Analysis (FNA) · 60 min consultation'),
      ).toBeInTheDocument()
    })

    it('goes back from date & time to the stage picker with the stage still selected', async () => {
      await renderBookMeeting()
      goToStagePicker()

      fireEvent.click(screen.getByRole('radio', { name: /Tax Education/i }))
      fireEvent.click(screen.getByRole('button', { name: /Continue to Date & Time/i }))
      fireEvent.click(screen.getByRole('button', { name: /Back to Advisory Stage/i }))

      expect(screen.getByText('Continue Your Financial Journey')).toBeInTheDocument()
      expect(screen.getByRole('radio', { name: /Tax Education/i })).toBeChecked()
    })

    it('shows the chosen stage in the booking summary', async () => {
      await renderBookMeeting()
      goToStagePicker()

      fireEvent.click(screen.getByRole('radio', { name: /Tax Education/i }))
      fireEvent.click(screen.getByRole('button', { name: /Continue to Date & Time/i }))
      fireEvent.click(screen.getByRole('button', { name: /Continue to Details/i }))

      expect(screen.getByText('Tax Education (45 min)')).toBeInTheDocument()
    })
  })
})
