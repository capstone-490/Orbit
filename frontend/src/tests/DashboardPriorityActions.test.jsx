// Substantial AI assistance used; verified with frontend tests.
import { act, cleanup, render, renderHook, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, describe, expect, it, vi } from 'vitest'
import DashboardAiCopilot from '../components/dashboard/DashboardAiCopilot'
import DashboardPriorityActions from '../components/dashboard/DashboardPriorityActions'
import {
  SUGGESTION_CACHE_KEY,
  SUGGESTION_CACHE_TTL_MS,
  usePriorityActions,
} from '../hooks/usePriorityActions'
import { updateFollowUp, updateFollowUpStatus } from '../services/FollowUpsApi'
import {
  getFollowUp,
  getPriorityActionSuggestions,
  getPriorityActions,
} from '../services/PriorityActionsApi'
import { getDueBadge } from '../utils/dueBadge'

vi.mock('../services/PriorityActionsApi', () => ({
  getFollowUp: vi.fn(),
  getPriorityActions: vi.fn(),
  getPriorityActionSuggestions: vi.fn(),
}))

vi.mock('../services/FollowUpsApi', () => ({
  updateFollowUp: vi.fn(),
  updateFollowUpStatus: vi.fn(),
}))

const ACTIONS = [
  {
    follow_up_id: 3,
    client_id: 4,
    client_name: 'John Doe',
    reason: 'Missing signature on compliance document',
    due_date: '2026-11-09',
    priority: 'High',
    status: 'In Progress',
    urgency: 'overdue',
    days_until_due: -1,
    urgency_reason: 'Overdue by 1 day',
  },
  {
    follow_up_id: 2,
    client_id: 4,
    client_name: 'John Doe',
    reason: 'Send educational documents',
    due_date: '2026-11-11',
    priority: 'Medium',
    status: 'Pending',
    urgency: 'due_soon',
    days_until_due: 1,
    urgency_reason: 'Due tomorrow',
  },
  {
    follow_up_id: 1,
    client_id: 3,
    client_name: 'Sara',
    reason: 'Complete application document',
    due_date: '2026-11-17',
    priority: 'High',
    status: 'Pending',
    urgency: 'high_priority',
    days_until_due: 7,
    urgency_reason: 'High priority, due in 7 days',
  },
]

afterEach(() => {
  cleanup()
  vi.clearAllMocks()
  vi.restoreAllMocks()
  window.sessionStorage.clear()
})

// --------------------------------------------------------------------------
// Urgent follow-ups (inside the Priority Tasks card)
// --------------------------------------------------------------------------

function renderPriorityActions(props = {}) {
  return render(
    <MemoryRouter>
      <DashboardPriorityActions
        actions={ACTIONS}
        total={3}
        loading={false}
        error=""
        onRetry={vi.fn()}
        onComplete={vi.fn().mockResolvedValue(undefined)}
        {...props}
      />
    </MemoryRouter>,
  )
}

describe('DashboardPriorityActions', () => {
  it('lists urgent follow-ups in API order with due badges', () => {
    renderPriorityActions()

    const items = screen.getAllByRole('listitem')
    expect(items).toHaveLength(3)
    expect(
      within(items[0]).getByText('Missing signature on compliance document'),
    ).toBeInTheDocument()
    expect(within(items[0]).getByText('OVERDUE')).toBeInTheDocument()
    expect(items[0]).toHaveClass('urgency-overdue')
    expect(within(items[1]).getByText('TOMORROW')).toBeInTheDocument()
    expect(within(items[2]).getByText('NOV 17')).toBeInTheDocument()
  })

  it('shows the client and reason without repeating the priority', () => {
    renderPriorityActions()

    const items = screen.getAllByRole('listitem')
    expect(items[0]).toHaveTextContent('John Doe · Overdue by 1 day · High priority')
    expect(items[2]).toHaveTextContent('Sara · High priority, due in 7 days')
    expect(items[2]).not.toHaveTextContent('days · High priority')
  })

  it('links to all follow-ups with the urgent total', () => {
    renderPriorityActions({ total: 8 })

    expect(screen.getByRole('link', { name: 'View all (8)' })).toHaveAttribute(
      'href',
      '/follow-ups',
    )
  })

  it('shows a loading state', () => {
    renderPriorityActions({ loading: true, actions: [] })

    expect(screen.getByRole('status')).toHaveTextContent('Loading urgent follow-ups…')
    expect(screen.queryByRole('link')).not.toBeInTheDocument()
  })

  it('shows an empty state', () => {
    renderPriorityActions({ actions: [], total: 0 })

    expect(screen.getByText("No urgent follow-ups. You're all caught up.")).toBeInTheDocument()
    expect(screen.queryByRole('link')).not.toBeInTheDocument()
  })

  it('shows an error with a working retry button', async () => {
    const onRetry = vi.fn()
    const user = userEvent.setup()
    renderPriorityActions({ actions: [], error: 'Could not load urgent follow-ups.', onRetry })

    const alert = screen.getByRole('alert')
    expect(alert).toHaveTextContent('Could not load urgent follow-ups.')
    await user.click(within(alert).getByRole('button', { name: 'Try again' }))
    expect(onRetry).toHaveBeenCalledTimes(1)
  })

  it('completes a follow-up when its checkbox is ticked', async () => {
    const onComplete = vi.fn().mockResolvedValue(undefined)
    const user = userEvent.setup()
    renderPriorityActions({ onComplete })

    await user.click(
      screen.getByRole('checkbox', {
        name: 'Mark "Missing signature on compliance document" as completed',
      }),
    )

    expect(onComplete).toHaveBeenCalledWith(3)
    expect(screen.queryByRole('alert')).not.toBeInTheDocument()
  })

  it('disables the checkbox while the update is in progress', async () => {
    let finish
    const onComplete = vi.fn(() => new Promise((resolve) => (finish = resolve)))
    const user = userEvent.setup()
    renderPriorityActions({ onComplete })

    const checkbox = screen.getAllByRole('checkbox')[1]
    await user.click(checkbox)
    expect(checkbox).toBeDisabled()

    await act(async () => finish())
    expect(checkbox).not.toBeDisabled()
  })

  it('shows an error when completing a follow-up fails', async () => {
    const onComplete = vi.fn().mockRejectedValue(new Error('Server error'))
    const user = userEvent.setup()
    renderPriorityActions({ onComplete })

    await user.click(screen.getAllByRole('checkbox')[0])

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'Could not update follow-up. Please try again.',
    )
    expect(screen.getAllByRole('listitem')).toHaveLength(3)
  })

  it('labels follow-ups due today', () => {
    expect(getDueBadge({ urgency: 'due_soon', days_until_due: 0, due_date: '2026-11-10' })).toEqual(
      {
        label: 'TODAY',
        tone: 'danger',
      },
    )
  })
})

// --------------------------------------------------------------------------
// AI Copilot card
// --------------------------------------------------------------------------

function renderCopilot(props = {}) {
  return render(
    <DashboardAiCopilot
      actions={ACTIONS}
      actionsLoading={false}
      aiStatus="available"
      suggestions={[]}
      onApprove={vi.fn().mockResolvedValue(undefined)}
      onDismiss={vi.fn()}
      onRefresh={vi.fn()}
      {...props}
    />,
  )
}

const SUGGESTION = { follow_up_id: 2, text: 'Email the tax documents today.' }

describe('DashboardAiCopilot', () => {
  it('shows each suggestion with the follow-up it refers to', () => {
    renderCopilot({
      suggestions: [{ follow_up_id: 2, text: 'Email the tax documents today.' }],
    })

    const item = screen.getByRole('listitem')
    expect(item).toHaveTextContent('Suggested next step')
    expect(item).toHaveTextContent('Send educational documents')
    expect(item).toHaveTextContent('Email the tax documents today.')
    expect(item).toHaveTextContent('John Doe')
  })

  it('still shows a suggestion whose follow-up is not in the visible list', () => {
    renderCopilot({ suggestions: [{ follow_up_id: 99, text: 'Call the client.' }] })

    expect(screen.getByRole('listitem')).toHaveTextContent('Call the client.')
  })

  it('shows a loading state while suggestions are generated', () => {
    renderCopilot({ aiStatus: 'loading' })

    expect(screen.getByRole('status')).toHaveTextContent('Generating suggestions…')
  })

  it('explains when AI is turned off', () => {
    renderCopilot({ aiStatus: 'disabled' })

    expect(screen.getByText('AI suggestions are turned off.')).toBeInTheDocument()
  })

  it('explains when AI is unavailable', () => {
    renderCopilot({ aiStatus: 'unavailable' })

    expect(screen.getByText(/AI suggestions are unavailable right now/)).toBeInTheDocument()
  })

  it('shows an empty state when AI has no suggestions', () => {
    renderCopilot({ suggestions: [] })

    expect(screen.getByText('No suggestions right now.')).toBeInTheDocument()
  })

  it('approves a suggestion with its follow-up id and text', async () => {
    const onApprove = vi.fn().mockResolvedValue(undefined)
    const user = userEvent.setup()
    renderCopilot({ suggestions: [SUGGESTION], onApprove })

    await user.click(screen.getByRole('button', { name: '✓ Approve' }))

    expect(onApprove).toHaveBeenCalledWith(2, 'Email the tax documents today.')
    expect(screen.queryByRole('alert')).not.toBeInTheDocument()
  })

  it('disables both buttons while an approval is saving', async () => {
    let finish
    const onApprove = vi.fn(() => new Promise((resolve) => (finish = resolve)))
    const user = userEvent.setup()
    renderCopilot({ suggestions: [SUGGESTION], onApprove })

    await user.click(screen.getByRole('button', { name: '✓ Approve' }))
    expect(screen.getByRole('button', { name: 'Saving…' })).toBeDisabled()
    expect(screen.getByRole('button', { name: 'Dismiss' })).toBeDisabled()

    await act(async () => finish())
    expect(screen.getByRole('button', { name: '✓ Approve' })).not.toBeDisabled()
  })

  it('shows an error when approving fails', async () => {
    const onApprove = vi.fn().mockRejectedValue(new Error('Server error'))
    const user = userEvent.setup()
    renderCopilot({ suggestions: [SUGGESTION], onApprove })

    await user.click(screen.getByRole('button', { name: '✓ Approve' }))

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'Could not save the suggestion. Please try again.',
    )
  })

  it('dismisses a suggestion', async () => {
    const onDismiss = vi.fn()
    const user = userEvent.setup()
    renderCopilot({ suggestions: [SUGGESTION], onDismiss })

    await user.click(screen.getByRole('button', { name: 'Dismiss' }))

    expect(onDismiss).toHaveBeenCalledWith(2)
  })

  it('shows an approved suggestion as saved, without approve or dismiss buttons', () => {
    renderCopilot({ suggestions: [{ ...SUGGESTION, approved: true }] })

    expect(screen.getByText('✓ Saved to follow-up notes')).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: '✓ Approve' })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Dismiss' })).not.toBeInTheDocument()
  })

  it('refreshes suggestions on request', async () => {
    const onRefresh = vi.fn()
    const user = userEvent.setup()
    renderCopilot({ suggestions: [SUGGESTION], onRefresh })

    await user.click(screen.getByRole('button', { name: 'Refresh AI suggestions' }))

    expect(onRefresh).toHaveBeenCalledTimes(1)
  })

  it('offers a refresh when AI is unavailable', () => {
    renderCopilot({ aiStatus: 'unavailable' })

    expect(screen.getByRole('button', { name: 'Refresh AI suggestions' })).toBeInTheDocument()
  })

  it.each(['disabled', 'loading'])('hides the refresh button when AI is %s', (aiStatus) => {
    renderCopilot({ aiStatus })

    expect(screen.queryByRole('button', { name: 'Refresh AI suggestions' })).not.toBeInTheDocument()
  })
})

// --------------------------------------------------------------------------
// Data loading hook
// --------------------------------------------------------------------------

describe('usePriorityActions', () => {
  it('loads urgent follow-ups and AI suggestions', async () => {
    getPriorityActions.mockResolvedValue({ items: ACTIONS, total: 3 })
    getPriorityActionSuggestions.mockResolvedValue({
      status: 'available',
      suggestions: [{ follow_up_id: 3, text: 'Send the signature request.' }],
    })

    const { result } = renderHook(() => usePriorityActions())

    expect(result.current.loading).toBe(true)
    await waitFor(() => expect(result.current.loading).toBe(false))
    await waitFor(() => expect(result.current.aiStatus).toBe('available'))
    expect(result.current.actions).toHaveLength(3)
    expect(result.current.total).toBe(3)
    expect(result.current.suggestions).toHaveLength(1)
    expect(getPriorityActions).toHaveBeenCalledWith(5)
  })

  it('treats a failed AI request as unavailable without failing the list', async () => {
    getPriorityActions.mockResolvedValue({ items: ACTIONS, total: 3 })
    getPriorityActionSuggestions.mockRejectedValue(new Error('Network down'))

    const { result } = renderHook(() => usePriorityActions())

    await waitFor(() => expect(result.current.aiStatus).toBe('unavailable'))
    await waitFor(() => expect(result.current.loading).toBe(false))
    expect(result.current.error).toBe('')
    expect(result.current.actions).toHaveLength(3)
  })

  it('reports an error and reloads on retry', async () => {
    getPriorityActions
      .mockRejectedValueOnce(new Error('Server error'))
      .mockResolvedValueOnce({ items: ACTIONS, total: 3 })
    getPriorityActionSuggestions.mockResolvedValue({ status: 'disabled', suggestions: [] })

    const { result } = renderHook(() => usePriorityActions())

    await waitFor(() => expect(result.current.error).toBe('Could not load urgent follow-ups.'))

    act(() => result.current.retry())

    await waitFor(() => expect(result.current.actions).toHaveLength(3))
    expect(result.current.error).toBe('')
    expect(getPriorityActions).toHaveBeenCalledTimes(2)
  })

  it('marks a follow-up completed and removes it from the list', async () => {
    getPriorityActions.mockResolvedValue({ items: ACTIONS, total: 3 })
    getPriorityActionSuggestions.mockResolvedValue({
      status: 'available',
      suggestions: [{ follow_up_id: 3, text: 'Send the signature request.' }],
    })
    updateFollowUpStatus.mockResolvedValue({ id: 3, status: 'Completed' })

    const { result } = renderHook(() => usePriorityActions())
    await waitFor(() => expect(result.current.aiStatus).toBe('available'))
    await waitFor(() => expect(result.current.actions).toHaveLength(3))

    await act(() => result.current.completeAction(3))

    expect(updateFollowUpStatus).toHaveBeenCalledWith(3, 'Completed')
    expect(result.current.actions.map((action) => action.follow_up_id)).toEqual([2, 1])
    expect(result.current.total).toBe(2)
    expect(result.current.suggestions).toEqual([])
  })

  it('keeps the follow-up in the list when completing it fails', async () => {
    getPriorityActions.mockResolvedValue({ items: ACTIONS, total: 3 })
    getPriorityActionSuggestions.mockResolvedValue({ status: 'disabled', suggestions: [] })
    updateFollowUpStatus.mockRejectedValue(new Error('Server error'))

    const { result } = renderHook(() => usePriorityActions())
    await waitFor(() => expect(result.current.actions).toHaveLength(3))

    await expect(act(() => result.current.completeAction(3))).rejects.toThrow('Server error')

    expect(result.current.actions).toHaveLength(3)
    expect(result.current.total).toBe(3)
  })

  it('approves a suggestion by appending it to the follow-up notes', async () => {
    getPriorityActions.mockResolvedValue({ items: ACTIONS, total: 3 })
    getPriorityActionSuggestions.mockResolvedValue({
      status: 'available',
      suggestions: [SUGGESTION],
    })
    getFollowUp.mockResolvedValue({ id: 2, discussion_notes: 'Called client on Monday.' })
    updateFollowUp.mockResolvedValue({ id: 2 })

    const { result } = renderHook(() => usePriorityActions())
    await waitFor(() => expect(result.current.suggestions).toHaveLength(1))

    await act(() => result.current.approveSuggestion(2, SUGGESTION.text))

    expect(getFollowUp).toHaveBeenCalledWith(2)
    expect(updateFollowUp).toHaveBeenCalledWith(2, {
      discussion_notes:
        'Called client on Monday.\n\nAI-suggested next step (approved): Email the tax documents today.',
    })
    expect(result.current.suggestions[0].approved).toBe(true)
  })

  it('approves a suggestion on a follow-up with no notes yet', async () => {
    getPriorityActions.mockResolvedValue({ items: ACTIONS, total: 3 })
    getPriorityActionSuggestions.mockResolvedValue({
      status: 'available',
      suggestions: [SUGGESTION],
    })
    getFollowUp.mockResolvedValue({ id: 2, discussion_notes: null })
    updateFollowUp.mockResolvedValue({ id: 2 })

    const { result } = renderHook(() => usePriorityActions())
    await waitFor(() => expect(result.current.suggestions).toHaveLength(1))

    await act(() => result.current.approveSuggestion(2, SUGGESTION.text))

    expect(updateFollowUp).toHaveBeenCalledWith(2, {
      discussion_notes: 'AI-suggested next step (approved): Email the tax documents today.',
    })
  })

  it('does not mark a suggestion approved when saving fails', async () => {
    getPriorityActions.mockResolvedValue({ items: ACTIONS, total: 3 })
    getPriorityActionSuggestions.mockResolvedValue({
      status: 'available',
      suggestions: [SUGGESTION],
    })
    getFollowUp.mockResolvedValue({ id: 2, discussion_notes: '' })
    updateFollowUp.mockRejectedValue(new Error('Server error'))

    const { result } = renderHook(() => usePriorityActions())
    await waitFor(() => expect(result.current.suggestions).toHaveLength(1))

    await expect(act(() => result.current.approveSuggestion(2, SUGGESTION.text))).rejects.toThrow(
      'Server error',
    )
    expect(result.current.suggestions[0].approved).toBeUndefined()
  })

  it('dismisses a suggestion without calling the API', async () => {
    getPriorityActions.mockResolvedValue({ items: ACTIONS, total: 3 })
    getPriorityActionSuggestions.mockResolvedValue({
      status: 'available',
      suggestions: [SUGGESTION],
    })

    const { result } = renderHook(() => usePriorityActions())
    await waitFor(() => expect(result.current.suggestions).toHaveLength(1))

    act(() => result.current.dismissSuggestion(2))

    expect(result.current.suggestions).toEqual([])
    expect(updateFollowUp).not.toHaveBeenCalled()
  })

  it('reuses cached suggestions when the dashboard is opened again', async () => {
    getPriorityActions.mockResolvedValue({ items: ACTIONS, total: 3 })
    getPriorityActionSuggestions.mockResolvedValue({
      status: 'available',
      suggestions: [SUGGESTION],
    })

    const first = renderHook(() => usePriorityActions())
    await waitFor(() => expect(first.result.current.suggestions).toHaveLength(1))
    first.unmount()

    const second = renderHook(() => usePriorityActions())
    await waitFor(() => expect(second.result.current.aiStatus).toBe('available'))

    expect(second.result.current.suggestions).toEqual([SUGGESTION])
    expect(getPriorityActionSuggestions).toHaveBeenCalledTimes(1)
  })

  it('regenerates suggestions once the cache is older than ten minutes', async () => {
    getPriorityActions.mockResolvedValue({ items: ACTIONS, total: 3 })
    getPriorityActionSuggestions.mockResolvedValue({
      status: 'available',
      suggestions: [SUGGESTION],
    })
    const start = Date.now()
    const now = vi.spyOn(Date, 'now').mockReturnValue(start)

    const first = renderHook(() => usePriorityActions())
    await waitFor(() => expect(first.result.current.suggestions).toHaveLength(1))
    first.unmount()

    now.mockReturnValue(start + SUGGESTION_CACHE_TTL_MS + 1)
    const second = renderHook(() => usePriorityActions())
    await waitFor(() => expect(getPriorityActionSuggestions).toHaveBeenCalledTimes(2))
    await waitFor(() => expect(second.result.current.aiStatus).toBe('available'))
  })

  it('regenerates suggestions when the urgent list has changed', async () => {
    getPriorityActions.mockResolvedValueOnce({ items: ACTIONS, total: 3 })
    getPriorityActionSuggestions.mockResolvedValue({
      status: 'available',
      suggestions: [SUGGESTION],
    })

    const first = renderHook(() => usePriorityActions())
    await waitFor(() => expect(first.result.current.suggestions).toHaveLength(1))
    first.unmount()

    getPriorityActions.mockResolvedValueOnce({ items: ACTIONS.slice(0, 2), total: 2 })
    renderHook(() => usePriorityActions())

    await waitFor(() => expect(getPriorityActionSuggestions).toHaveBeenCalledTimes(2))
  })

  it('does not reuse suggestions cached for a different set of follow-ups', async () => {
    window.sessionStorage.setItem(
      SUGGESTION_CACHE_KEY,
      JSON.stringify({
        savedAt: Date.now(),
        actionIds: [91, 92],
        status: 'available',
        suggestions: [{ follow_up_id: 91, text: "Someone else's suggestion." }],
        handledIds: [],
      }),
    )
    getPriorityActions.mockResolvedValue({ items: ACTIONS, total: 3 })
    getPriorityActionSuggestions.mockResolvedValue({
      status: 'available',
      suggestions: [SUGGESTION],
    })

    const { result } = renderHook(() => usePriorityActions())

    await waitFor(() => expect(result.current.suggestions).toEqual([SUGGESTION]))
    expect(getPriorityActionSuggestions).toHaveBeenCalledTimes(1)
  })

  it('keeps a dismissed suggestion hidden when the dashboard is opened again', async () => {
    getPriorityActions.mockResolvedValue({ items: ACTIONS, total: 3 })
    getPriorityActionSuggestions.mockResolvedValue({
      status: 'available',
      suggestions: [SUGGESTION, { follow_up_id: 3, text: 'Send the signature request.' }],
    })

    const first = renderHook(() => usePriorityActions())
    await waitFor(() => expect(first.result.current.suggestions).toHaveLength(2))
    act(() => first.result.current.dismissSuggestion(2))
    first.unmount()

    const second = renderHook(() => usePriorityActions())
    await waitFor(() => expect(second.result.current.aiStatus).toBe('available'))

    expect(second.result.current.suggestions.map((s) => s.follow_up_id)).toEqual([3])
  })

  it('keeps dismissed follow-ups hidden when suggestions are regenerated', async () => {
    getPriorityActions.mockResolvedValueOnce({ items: ACTIONS, total: 3 })
    getPriorityActionSuggestions.mockResolvedValue({
      status: 'available',
      suggestions: [SUGGESTION],
    })

    const first = renderHook(() => usePriorityActions())
    await waitFor(() => expect(first.result.current.suggestions).toHaveLength(1))
    act(() => first.result.current.dismissSuggestion(2))
    first.unmount()

    getPriorityActions.mockResolvedValueOnce({ items: ACTIONS.slice(0, 2), total: 2 })
    const second = renderHook(() => usePriorityActions())

    await waitFor(() => expect(getPriorityActionSuggestions).toHaveBeenCalledTimes(2))
    await waitFor(() => expect(second.result.current.aiStatus).toBe('available'))
    expect(second.result.current.suggestions).toEqual([])
  })

  it('keeps an approved suggestion marked as saved when the dashboard is opened again', async () => {
    getPriorityActions.mockResolvedValue({ items: ACTIONS, total: 3 })
    getPriorityActionSuggestions.mockResolvedValue({
      status: 'available',
      suggestions: [SUGGESTION],
    })
    getFollowUp.mockResolvedValue({ id: 2, discussion_notes: '' })
    updateFollowUp.mockResolvedValue({ id: 2 })

    const first = renderHook(() => usePriorityActions())
    await waitFor(() => expect(first.result.current.suggestions).toHaveLength(1))
    await act(() => first.result.current.approveSuggestion(2, SUGGESTION.text))
    first.unmount()

    const second = renderHook(() => usePriorityActions())
    await waitFor(() => expect(second.result.current.aiStatus).toBe('available'))

    expect(second.result.current.suggestions[0].approved).toBe(true)
    expect(getPriorityActionSuggestions).toHaveBeenCalledTimes(1)
  })

  it('refresh ignores the cache and brings back dismissed follow-ups', async () => {
    getPriorityActions.mockResolvedValue({ items: ACTIONS, total: 3 })
    getPriorityActionSuggestions.mockResolvedValue({
      status: 'available',
      suggestions: [SUGGESTION],
    })

    const { result } = renderHook(() => usePriorityActions())
    await waitFor(() => expect(result.current.suggestions).toHaveLength(1))
    act(() => result.current.dismissSuggestion(2))
    expect(result.current.suggestions).toEqual([])

    act(() => result.current.refreshSuggestions())

    await waitFor(() => expect(getPriorityActionSuggestions).toHaveBeenCalledTimes(2))
    await waitFor(() => expect(result.current.suggestions).toEqual([SUGGESTION]))
  })

  it('completing a follow-up does not regenerate the other suggestions', async () => {
    getPriorityActions.mockResolvedValue({ items: ACTIONS, total: 3 })
    getPriorityActionSuggestions.mockResolvedValue({
      status: 'available',
      suggestions: [SUGGESTION, { follow_up_id: 3, text: 'Send the signature request.' }],
    })
    updateFollowUpStatus.mockResolvedValue({ id: 3, status: 'Completed' })

    const { result } = renderHook(() => usePriorityActions())
    await waitFor(() => expect(result.current.suggestions).toHaveLength(2))

    await act(() => result.current.completeAction(3))

    await waitFor(() => expect(result.current.suggestions).toEqual([SUGGESTION]))
    expect(getPriorityActionSuggestions).toHaveBeenCalledTimes(1)
  })

  it('does not cache suggestions while AI is turned off', async () => {
    getPriorityActions.mockResolvedValue({ items: ACTIONS, total: 3 })
    getPriorityActionSuggestions.mockResolvedValue({ status: 'disabled', suggestions: [] })

    const { result } = renderHook(() => usePriorityActions())
    await waitFor(() => expect(result.current.aiStatus).toBe('disabled'))

    expect(window.sessionStorage.getItem(SUGGESTION_CACHE_KEY)).toBeNull()
  })

  it('skips AI suggestions when the urgent list fails to load', async () => {
    getPriorityActions.mockRejectedValue(new Error('Server error'))

    const { result } = renderHook(() => usePriorityActions())

    await waitFor(() => expect(result.current.aiStatus).toBe('unavailable'))
    expect(getPriorityActionSuggestions).not.toHaveBeenCalled()
  })
})
