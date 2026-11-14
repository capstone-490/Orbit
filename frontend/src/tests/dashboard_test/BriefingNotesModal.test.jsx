import { cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import '@testing-library/jest-dom/vitest'
import BriefingNotesModal from '../../components/dashboard/BriefingNotesModal'
import { getMeetingBriefingNotes } from '../../services/MeetingApi'

vi.mock('../../services/MeetingApi', () => ({
  getMeetingBriefingNotes: vi.fn(),
}))

const meeting = {
  id: 42,
  clientName: 'Sarah Smith',
  time: '2026-11-12T14:00:00',
  duration: '30 min',
  completionStatus: 'Scheduled',
}

const notes = [
  {
    id: 1,
    title: 'Investment Goals',
    content: 'Discuss retirement planning.',
    created_at: '2026-10-20T12:00:00Z',
  },
  {
    id: 2,
    title: 'Risk Profile',
    content: 'Client prefers low-risk investments.',
    created_at: '2026-10-21T12:00:00Z',
  },
]

const setup = () => {
  const onClose = vi.fn()
  const result = render(<BriefingNotesModal meeting={meeting} onClose={onClose} />)
  return { onClose, ...result }
}

beforeEach(() => {
  vi.clearAllMocks()
})

afterEach(() => {
  cleanup()
})

describe('BriefingNotesModal', () => {
  it('displays meeting information alongside the briefing notes', async () => {
    getMeetingBriefingNotes.mockResolvedValue(notes)

    setup()

    const dialog = screen.getByRole('dialog', {
      name: 'Meeting Details',
    })

    expect(dialog).toBeInTheDocument()

    expect(within(dialog).getByRole('heading', { name: 'Briefing Notes' })).toBeInTheDocument()

    expect(within(dialog).getByText('Client')).toBeInTheDocument()
    expect(within(dialog).getByText('Date & Time')).toBeInTheDocument()
    expect(within(dialog).getByText('Duration')).toBeInTheDocument()
    expect(within(dialog).getByText('Status')).toBeInTheDocument()

    expect(within(dialog).getByText('30 min')).toBeInTheDocument()
    expect(within(dialog).getByText('Scheduled')).toBeInTheDocument()

    expect(within(dialog).getByText(/Nov 12, 2026.*2:00/i)).toBeInTheDocument()

    expect(await within(dialog).findByText('Investment Goals')).toBeInTheDocument()
  })
  it('loads and displays notes for the selected meeting', async () => {
    getMeetingBriefingNotes.mockResolvedValue(notes)

    setup()

    expect(screen.getByRole('dialog')).toBeInTheDocument()
    expect(screen.getByText('Sarah Smith')).toBeInTheDocument()

    await waitFor(() => {
      expect(getMeetingBriefingNotes).toHaveBeenCalledWith(42)
    })

    expect(await screen.findByText('Investment Goals')).toBeInTheDocument()
    expect(screen.getByText('Discuss retirement planning.')).toBeInTheDocument()
    expect(screen.getByText('Risk Profile')).toBeInTheDocument()
    expect(screen.getByText('Client prefers low-risk investments.')).toBeInTheDocument()
  })

  it('shows a loading state while fetching notes', () => {
    getMeetingBriefingNotes.mockReturnValue(new Promise(() => {}))

    setup()

    expect(screen.getByRole('status')).toHaveTextContent('Loading briefing notes...')
  })

  it('shows an empty state when no notes exist', async () => {
    getMeetingBriefingNotes.mockResolvedValue([])

    setup()

    expect(
      await screen.findByText('No briefing notes are available for this meeting.'),
    ).toBeInTheDocument()
  })

  it('displays API errors without closing the modal', async () => {
    getMeetingBriefingNotes.mockRejectedValue(new Error('Unable to load briefing notes.'))

    const { onClose } = setup()

    expect(await screen.findByRole('alert')).toHaveTextContent('Unable to load briefing notes.')

    expect(onClose).not.toHaveBeenCalled()
    expect(screen.getByRole('dialog')).toBeInTheDocument()
  })

  it('displays an error for an inaccessible meeting', async () => {
    getMeetingBriefingNotes.mockRejectedValue(new Error('Meeting not found.'))

    setup()

    expect(await screen.findByRole('alert')).toHaveTextContent('Meeting not found.')
  })

  it('closes when the close button is clicked', async () => {
    getMeetingBriefingNotes.mockResolvedValue([])

    const { onClose } = setup()

    await screen.findByText('No briefing notes are available for this meeting.')

    fireEvent.click(screen.getByRole('button', { name: 'Close', exact: true }))

    expect(onClose).toHaveBeenCalledOnce()
  })

  it('closes when the backdrop is clicked', async () => {
    getMeetingBriefingNotes.mockResolvedValue([])

    const { onClose } = setup()

    await screen.findByText('No briefing notes are available for this meeting.')

    fireEvent.click(screen.getByRole('button', { name: 'Close briefing notes' }))

    expect(onClose).toHaveBeenCalledOnce()
  })

  it('closes when Escape is pressed', async () => {
    getMeetingBriefingNotes.mockResolvedValue([])

    const { onClose } = setup()

    await screen.findByText('No briefing notes are available for this meeting.')

    fireEvent.keyDown(document, { key: 'Escape' })

    expect(onClose).toHaveBeenCalledOnce()
  })

  it('ignores a stale response after unmounting', async () => {
    let resolveRequest

    getMeetingBriefingNotes.mockReturnValue(
      new Promise((resolve) => {
        resolveRequest = resolve
      }),
    )

    const { unmount } = setup()

    unmount()
    resolveRequest(notes)

    await Promise.resolve()

    expect(screen.queryByText('Investment Goals')).not.toBeInTheDocument()
  })

  it('focuses the close button when the modal opens', async () => {
    getMeetingBriefingNotes.mockResolvedValue([])

    setup()

    expect(screen.getByRole('button', { name: 'Close', exact: true })).toHaveFocus()

    await screen.findByText('No briefing notes are available for this meeting.')
  })

  it('keeps keyboard focus inside the modal when Tab is pressed', async () => {
    getMeetingBriefingNotes.mockResolvedValue([])

    setup()

    const closeButton = screen.getByRole('button', {
      name: 'Close',
      exact: true,
    })

    expect(closeButton).toHaveFocus()

    fireEvent.keyDown(document, { key: 'Tab' })

    expect(closeButton).toHaveFocus()

    fireEvent.keyDown(document, { key: 'Tab', shiftKey: true })

    expect(closeButton).toHaveFocus()

    await screen.findByText('No briefing notes are available for this meeting.')
  })

  it('wraps keyboard focus between the first and last focusable elements', async () => {
    getMeetingBriefingNotes.mockResolvedValue([])

    const rectsSpy = vi.spyOn(HTMLElement.prototype, 'getClientRects').mockReturnValue([{}])

    try {
      setup()

      await screen.findByText('No briefing notes are available for this meeting.')

      const dialog = screen.getByRole('dialog')
      const closeButton = within(dialog).getByRole('button', {
        name: 'Close',
        exact: true,
      })

      // Add another focusable element inside the dialog.
      const secondButton = document.createElement('button')
      secondButton.textContent = 'Second action'
      dialog.appendChild(secondButton)

      // Shift+Tab from the first element wraps to the last.
      closeButton.focus()
      fireEvent.keyDown(document, { key: 'Tab', shiftKey: true })

      expect(secondButton).toHaveFocus()

      // Tab from the last element wraps back to the first.
      fireEvent.keyDown(document, { key: 'Tab' })

      expect(closeButton).toHaveFocus()
    } finally {
      rectsSpy.mockRestore()
    }
  })

  it('restores focus to the previously focused element when closed', async () => {
    getMeetingBriefingNotes.mockResolvedValue([])

    const trigger = document.createElement('button')
    trigger.textContent = 'Open briefing notes'
    document.body.appendChild(trigger)
    trigger.focus()

    try {
      const { unmount } = setup()

      const closeButton = screen.getByRole('button', {
        name: 'Close',
        exact: true,
      })

      expect(closeButton).toHaveFocus()

      await screen.findByText('No briefing notes are available for this meeting.')

      unmount()

      expect(trigger).toHaveFocus()
    } finally {
      trigger.remove()
    }
  })
})
