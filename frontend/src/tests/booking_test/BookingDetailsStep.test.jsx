// Substantial AI assistance used; verified with frontend tests and production build.
import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import BookingDetailsStep from '../../components/booking/BookingDetailsStep'

afterEach(() => {
  cleanup()
  vi.restoreAllMocks()
})

describe('BookingDetailsStep', () => {
  const booking = {
    selectedType: 'introduction',
    selectedDate: new Date(2026, 10, 20),
    selectedTime: '09:30 AM',
    advisor: {
      firstName: 'John',
      lastName: 'Smith',
      designation: 'CFP',
    },
  }

  const renderDetails = (props = {}) => {
    const callbacks = {
      onBack: vi.fn(),
      onChangeBooking: vi.fn(),
    }

    render(<BookingDetailsStep {...booking} {...callbacks} {...props} />)
    return callbacks
  }

  it('shows the booking summary', () => {
    renderDetails()

    expect(screen.getByText(/Introduction Meeting/)).toBeInTheDocument()
    expect(screen.getByText(/09:30 AM/)).toBeInTheDocument()
    expect(screen.getByText(/John Smith, CFP/)).toBeInTheDocument()
  })

  it('shows a follow-up consultation', () => {
    renderDetails({ selectedType: 'follow-up' })

    expect(screen.getByText(/Follow-up Consultation/)).toBeInTheDocument()
  })

  it('shows required contact fields', () => {
    renderDetails()

    const requiredFields = ['First Name', 'Last Name', 'Email Address']

    requiredFields.forEach((field) => {
      expect(screen.getByLabelText(new RegExp(field, 'i'))).toBeRequired()
    })
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

  it('handles form submission without logging client information', () => {
    const consoleSpy = vi.spyOn(console, 'log').mockImplementation(() => {})

    renderDetails()

    const details = {
      'First Name': 'Daniel',
      'Last Name': 'Foster',
      'Email Address': 'daniel@example.com',
    }

    Object.entries(details).forEach(([label, value]) => {
      fireEvent.change(screen.getByLabelText(new RegExp(label, 'i')), {
        target: { value },
      })
    })

    fireEvent.click(screen.getByRole('button', { name: /Confirm & Schedule Meeting/i }))

    expect(consoleSpy).not.toHaveBeenCalled()
  })
})
