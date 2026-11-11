import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { getAdvisorMeetings, rescheduleMeeting } from '../services/MeetingApi'

describe('MeetingApi', () => {
  beforeEach(() => {
    vi.stubGlobal('fetch', vi.fn())
  })

  afterEach(() => {
    vi.unstubAllGlobals()
  })

  describe('getAdvisorMeetings', () => {
    it('loads meetings for a valid advisor', async () => {
      const meetings = [{ id: 5, advisor_id: 12 }]

      fetch.mockResolvedValue({
        ok: true,
        json: async () => meetings,
      })

      await expect(getAdvisorMeetings(12)).resolves.toEqual(meetings)

      expect(fetch).toHaveBeenCalledWith(expect.stringMatching(/\/meetings\/12$/), {
        credentials: 'include',
      })
    })

    it.each([0, -1, 1.5, NaN, null, undefined, 'abc'])(
      'rejects invalid advisor ID %s',
      async (advisorId) => {
        await expect(getAdvisorMeetings(advisorId)).rejects.toThrow(
          'advisorId must be a positive integer.',
        )
        expect(fetch).not.toHaveBeenCalled()
      },
    )

    it('throws when loading meetings fails', async () => {
      fetch.mockResolvedValue({ ok: false, status: 403 })

      await expect(getAdvisorMeetings(12)).rejects.toThrow('Unable to load meetings.')
    })
  })

  describe('rescheduleMeeting', () => {
    const newStart = '2030-06-01T10:00:00.000Z'

    it('sends a PATCH request and returns the updated meeting', async () => {
      const updated = { id: 5, meeting_date: newStart }

      fetch.mockResolvedValue({
        ok: true,
        json: async () => updated,
      })

      await expect(rescheduleMeeting(5, newStart)).resolves.toEqual(updated)

      expect(fetch).toHaveBeenCalledWith(expect.stringMatching(/\/meetings\/5\/reschedule$/), {
        method: 'PATCH',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ new_start: newStart }),
      })
    })

    it.each([0, -3, 2.5, NaN, null, undefined, 'abc'])(
      'rejects invalid meeting ID %s',
      async (meetingId) => {
        await expect(rescheduleMeeting(meetingId, newStart)).rejects.toThrow(
          'meetingId must be a positive integer.',
        )
        expect(fetch).not.toHaveBeenCalled()
      },
    )

    it.each([null, undefined, '', ' ', 'not-a-date', 12345])(
      'rejects invalid start date %s',
      async (value) => {
        await expect(rescheduleMeeting(5, value)).rejects.toThrow('newStart must be a valid date.')
        expect(fetch).not.toHaveBeenCalled()
      },
    )

    it('preserves a conflict error message and status', async () => {
      fetch.mockResolvedValue({
        ok: false,
        status: 409,
        json: async () => ({ detail: 'Meeting time conflicts with another booking.' }),
      })

      const error = await rescheduleMeeting(5, newStart).catch((err) => err)

      expect(error).toBeInstanceOf(Error)
      expect(error.message).toBe('Meeting time conflicts with another booking.')
      expect(error.status).toBe(409)
    })

    it('uses a fallback message when the error response is not JSON', async () => {
      fetch.mockResolvedValue({
        ok: false,
        status: 500,
        json: async () => {
          throw new SyntaxError('Invalid JSON')
        },
      })

      await expect(rescheduleMeeting(5, newStart)).rejects.toThrow(
        'Unable to reschedule the meeting. Please try again.',
      )
    })

    it('uses a fallback when the error detail is not a string', async () => {
      fetch.mockResolvedValue({
        ok: false,
        status: 422,
        json: async () => ({ detail: [{ msg: 'Invalid input' }] }),
      })

      await expect(rescheduleMeeting(5, newStart)).rejects.toThrow(
        'Unable to reschedule the meeting. Please try again.',
      )
    })

    it('propagates network failures', async () => {
      fetch.mockRejectedValue(new TypeError('Network unavailable'))

      await expect(rescheduleMeeting(5, newStart)).rejects.toThrow('Network unavailable')
    })
  })
})
