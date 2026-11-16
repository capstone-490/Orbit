import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import AdvisorStep from '../../components/booking/AdvisorStep'
import { getBookableAdvisors } from '../../services/BookingApi'

vi.mock('../../services/BookingApi', () => ({
  getBookableAdvisors: vi.fn(),
}))

const ADVISORS = [
  { id: 1, username: 'nsaba' },
  { id: 4, username: 'jsmith' },
]

afterEach(cleanup)

describe('AdvisorStep', () => {
  beforeEach(() => {
    getBookableAdvisors.mockReset()
  })

  const renderStep = (props = {}) => {
    const handlers = {
      onSelectAdvisor: vi.fn(),
      onContinue: vi.fn(),
      onAdvisorLogin: vi.fn(),
    }

    render(<AdvisorStep selectedAdvisorId={null} {...handlers} {...props} />)

    return handlers
  }

  it('lists the advisors who can be booked', async () => {
    getBookableAdvisors.mockResolvedValue(ADVISORS)
    renderStep()

    expect(screen.getByText('Loading advisors...')).toBeInTheDocument()
    expect(await screen.findByRole('radio', { name: /nsaba/ })).toBeInTheDocument()
    expect(screen.getByRole('radio', { name: /jsmith/ })).toBeInTheDocument()
  })

  it('selects an advisor', async () => {
    getBookableAdvisors.mockResolvedValue(ADVISORS)
    const { onSelectAdvisor } = renderStep()

    fireEvent.click(await screen.findByRole('radio', { name: /jsmith/ }))

    expect(onSelectAdvisor).toHaveBeenCalledWith({ id: 4, username: 'jsmith' })
  })

  it('disables continue until an advisor is selected', async () => {
    getBookableAdvisors.mockResolvedValue(ADVISORS)
    renderStep()

    await screen.findByRole('radio', { name: /nsaba/ })

    expect(screen.getByRole('button', { name: /Continue to Session Type/i })).toBeDisabled()
  })

  it('continues with the selected advisor', async () => {
    getBookableAdvisors.mockResolvedValue(ADVISORS)
    const { onContinue } = renderStep({ selectedAdvisorId: 1 })

    expect(await screen.findByRole('radio', { name: /nsaba/ })).toBeChecked()
    fireEvent.click(screen.getByRole('button', { name: /Continue to Session Type/i }))

    expect(onContinue).toHaveBeenCalledTimes(1)
  })

  it('says when no advisors are accepting bookings', async () => {
    getBookableAdvisors.mockResolvedValue([])
    renderStep()

    expect(await screen.findByText(/No advisors are accepting online bookings/)).toBeInTheDocument()
  })

  it('shows an error and retries', async () => {
    getBookableAdvisors
      .mockRejectedValueOnce(new Error('Unable to load advisors. Please try again.'))
      .mockResolvedValueOnce(ADVISORS)
    renderStep()

    expect(await screen.findByRole('alert')).toHaveTextContent('Unable to load advisors.')

    fireEvent.click(screen.getByRole('button', { name: 'Try Again' }))

    expect(await screen.findByRole('radio', { name: /nsaba/ })).toBeInTheDocument()
    expect(getBookableAdvisors).toHaveBeenCalledTimes(2)
  })

  it('links to the advisor login', async () => {
    getBookableAdvisors.mockResolvedValue([])
    const { onAdvisorLogin } = renderStep()

    await screen.findByText(/No advisors are accepting online bookings/)
    fireEvent.click(screen.getByRole('button', { name: 'Advisor Login' }))

    expect(onAdvisorLogin).toHaveBeenCalledTimes(1)
  })
})
