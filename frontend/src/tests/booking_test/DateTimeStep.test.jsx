import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import DateTimeStep from '../../components/booking/DateTimeStep'
import { getAvailableTimes } from '../../services/BookingApi'

vi.mock('../../services/BookingApi', () => ({
  getAvailableTimes: vi.fn(),
}))

const availableTimes = ['09:30 AM', '10:30 AM']
const selectedDate = new Date(2026, 10, 20)

beforeEach(() => {
  vi.clearAllMocks()
  getAvailableTimes.mockResolvedValue(availableTimes)
})

afterEach(() => {
  cleanup()
  vi.restoreAllMocks()
})

describe('DateTimeStep', () => {
  const renderDateTime = (overrides = {}) => {
    const props = {
      selectedDate,
      selectedTime: null,
      setSelectedDate: vi.fn(),
      setSelectedTime: vi.fn(),
      onBack: vi.fn(),
      onContinue: vi.fn(),
      ...overrides,
    }

    render(<DateTimeStep {...props} />)
    return props
  }

  it('asks the user to select a date', () => {
    renderDateTime({ selectedDate: null })

    expect(screen.getByText('Select a date to see available times.')).toBeInTheDocument()
    expect(getAvailableTimes).not.toHaveBeenCalled()
  })

  it('loads available times for the selected date', async () => {
    renderDateTime()

    expect(await screen.findByText('2 slots free')).toBeInTheDocument()
    expect(getAvailableTimes).toHaveBeenCalledWith(selectedDate)

    availableTimes.forEach((time) => {
      expect(screen.getByRole('button', { name: time })).toBeInTheDocument()
    })
  })

  it('shows loading while fetching available times', async () => {
    let resolveTimes

    getAvailableTimes.mockImplementation(
      () =>
        new Promise((resolve) => {
          resolveTimes = resolve
        }),
    )

    renderDateTime()

    expect(screen.getByText('Loading available times...')).toBeInTheDocument()

    resolveTimes(availableTimes)

    expect(await screen.findByText('2 slots free')).toBeInTheDocument()
  })

  it('clears the previous selected time', async () => {
    const { setSelectedTime } = renderDateTime()

    await waitFor(() => {
      expect(setSelectedTime).toHaveBeenCalledWith(null)
    })
  })

  it('allows the user to select an available time', async () => {
    const { setSelectedTime } = renderDateTime()

    fireEvent.click(await screen.findByRole('button', { name: '09:30 AM' }))

    expect(setSelectedTime).toHaveBeenCalledWith('09:30 AM')
  })

  it('highlights the selected time', async () => {
    renderDateTime({ selectedTime: '09:30 AM' })

    const timeButton = await screen.findByRole('button', { name: '09:30 AM' })

    expect(timeButton).toHaveClass('selected')
  })

  it('handles errors when loading times', async () => {
    getAvailableTimes.mockRejectedValue(new Error('API error'))
    const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {})

    renderDateTime()

    expect(await screen.findByText('0 slots free')).toBeInTheDocument()
    expect(consoleSpy).toHaveBeenCalled()
  })

  it('disables Continue when no time is selected', async () => {
    renderDateTime()

    await screen.findByText('2 slots free')

    expect(screen.getByRole('button', { name: /Continue to Details/i })).toBeDisabled()
  })

  it('continues when a time is selected', async () => {
    const { onContinue } = renderDateTime({ selectedTime: '09:30 AM' })

    await screen.findByText('2 slots free')

    fireEvent.click(screen.getByRole('button', { name: /Continue to Details/i }))

    expect(onContinue).toHaveBeenCalledOnce()
  })

  it('returns to the previous step', () => {
    const { onBack } = renderDateTime({ selectedDate: null })

    fireEvent.click(screen.getByRole('button', { name: /Back to Session Type/i }))

    expect(onBack).toHaveBeenCalledOnce()
  })
})
