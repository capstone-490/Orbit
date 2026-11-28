import { cleanup, render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, describe, expect, it, vi } from 'vitest'
import ClientReschedule from '../pages/ClientReschedule'

afterEach(() => {
  cleanup()
  vi.unstubAllGlobals()
})

describe('ClientReschedule', () => {
  it('loads the meeting using the secure link without requiring sign-in', async () => {
    const token = 'x'.repeat(43)
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: true,
        json: async () => ({
          meeting_date: '2030-06-01T10:00:00+00:00',
          duration_minutes: 30,
          advisor_name: 'Advisor',
        }),
      }),
    )

    render(
      <MemoryRouter initialEntries={[`/reschedule-meeting?token=${token}`]}>
        <ClientReschedule />
      </MemoryRouter>,
    )

    expect(await screen.findByText(/Meeting with Advisor/)).toBeInTheDocument()
    expect(screen.getByLabelText('New start time')).toBeInTheDocument()
    expect(fetch).toHaveBeenCalledWith(
      expect.stringMatching(/\/meetings\/client-reschedule\?token=/),
    )
  })
})
