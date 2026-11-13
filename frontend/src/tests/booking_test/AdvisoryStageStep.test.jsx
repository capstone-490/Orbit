// Substantial AI assistance used; verified with frontend tests and production build.
import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import AdvisoryStageStep from '../../components/booking/AdvisoryStageStep'
import { advisoryStages } from '../../data/advisoryStages'

afterEach(cleanup)

describe('AdvisoryStageStep', () => {
  const renderStep = (props = {}) => {
    const handlers = {
      onSelectStage: vi.fn(),
      onBack: vi.fn(),
      onContinue: vi.fn(),
    }

    render(
      <AdvisoryStageStep stages={advisoryStages} selectedStageId={null} {...handlers} {...props} />,
    )

    return handlers
  }

  it('renders the heading and every advisory stage', () => {
    renderStep()

    expect(screen.getByText('Continue Your Financial Journey')).toBeInTheDocument()

    for (const stage of advisoryStages) {
      expect(screen.getByText(stage.title)).toBeInTheDocument()
      expect(screen.getByText(`Stage ${stage.stage}`)).toBeInTheDocument()
    }

    expect(screen.getAllByRole('radio')).toHaveLength(advisoryStages.length)
  })

  it('calls onSelectStage with the clicked stage id', () => {
    const { onSelectStage } = renderStep()

    fireEvent.click(screen.getByRole('radio', { name: /Tax Education/i }))

    expect(onSelectStage).toHaveBeenCalledWith('tax-education')
  })

  it('marks only the selected stage as checked', () => {
    renderStep({ selectedStageId: 'tax-education' })

    const taxOption = screen.getByRole('radio', { name: /Tax Education/i })

    expect(taxOption).toBeChecked()
    expect(taxOption.closest('label')).toHaveClass('selected')
    expect(screen.getByRole('radio', { name: /Insurance Education/i })).not.toBeChecked()
  })

  it('disables continue until a stage is selected', () => {
    renderStep()

    expect(screen.getByRole('button', { name: /Continue to Date & Time/i })).toBeDisabled()
  })

  it('continues and goes back through the handlers', () => {
    const { onBack, onContinue } = renderStep({ selectedStageId: 'tax-education' })

    fireEvent.click(screen.getByRole('button', { name: /Continue to Date & Time/i }))
    fireEvent.click(screen.getByRole('button', { name: /Back to Session Type/i }))

    expect(onContinue).toHaveBeenCalledTimes(1)
    expect(onBack).toHaveBeenCalledTimes(1)
  })
})
