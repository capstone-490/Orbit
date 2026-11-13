// Substantial AI assistance used; verified with frontend tests and production build.
import { cleanup, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it } from 'vitest'
import BookingSteps from '../../components/booking/BookingSteps'

afterEach(cleanup)

describe('BookingSteps', () => {
  const renderSteps = (currentStep, titles) => {
    const { container } = render(<BookingSteps currentStep={currentStep} titles={titles} />)
    return container.querySelectorAll('.booking-step')
  }

  it('shows all booking steps', () => {
    renderSteps(1, ['Select Type', 'Date & Time', 'Details'])

    for (const title of ['Select Type', 'Date & Time', 'Details']) {
      expect(screen.getByText(title)).toBeInTheDocument()
    }
  })

  it('shows custom step titles when provided', () => {
    renderSteps(1, ['Advisory Stage', 'Date & Time', 'Client Details'])

    for (const title of ['Advisory Stage', 'Date & Time', 'Client Details']) {
      expect(screen.getByText(title)).toBeInTheDocument()
    }
    expect(screen.queryByText('Select Type')).not.toBeInTheDocument()
  })

  it('marks the first step as active', () => {
    const steps = renderSteps(1)

    expect(steps[0]).toHaveClass('active')
    expect(steps[1]).not.toHaveClass('active')
  })

  it('marks completed steps correctly', () => {
    const steps = renderSteps(3)

    expect(steps[0]).toHaveClass('completed')
    expect(steps[1]).toHaveClass('completed')
    expect(steps[2]).toHaveClass('active')
  })

  it('marks the second step as active', () => {
    const steps = renderSteps(2)

    expect(steps[0]).toHaveClass('completed')
    expect(steps[1]).toHaveClass('active')
    expect(steps[2]).not.toHaveClass('active')
  })
})
