import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import {
  bookMeeting,
  getAvailableTimes,
  getBookableAdvisors,
  toBookingStart,
} from '../services/BookingApi'

describe('BookingApi', () => {
  beforeEach(() => {
    vi.stubGlobal('fetch', vi.fn())
  })

  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('returns the available times', async () => {
    await expect(getAvailableTimes()).resolves.toContain('09:30 AM')
  })

  describe('getBookableAdvisors', () => {
    it('loads advisors from the public Google Meet route', async () => {
      const advisors = [{ id: 1, username: 'nsaba' }]
      fetch.mockResolvedValue({ ok: true, json: async () => advisors })

      await expect(getBookableAdvisors()).resolves.toEqual(advisors)
      expect(fetch).toHaveBeenCalledWith(
        expect.stringMatching(/\/google-meet-integration\/advisors$/),
      )
    })

    it('throws when the request fails', async () => {
      fetch.mockResolvedValue({ ok: false, status: 500 })

      await expect(getBookableAdvisors()).rejects.toThrow('Unable to load advisors.')
    })
  })

  describe('bookMeeting', () => {
    const booking = {
      name: 'Daniel Foster',
      email: 'daniel@example.com',
      phone_number: '5035550167',
      title: 'Introduction Meeting',
      start: '2026-11-19T10:30:00-05:00',
      duration_minutes: 45,
    }

    it('posts the booking to the advisor', async () => {
      const result = { meeting_id: 3, meeting_uri: 'https://meet.google.com/abc-defg-hij' }
      fetch.mockResolvedValue({ ok: true, json: async () => result })

      await expect(bookMeeting(4, booking)).resolves.toEqual(result)

      const [url, options] = fetch.mock.calls[0]
      expect(url).toMatch(/\/google-meet-integration\/book\/4$/)
      expect(options.method).toBe('POST')
      expect(options.headers).toEqual({ 'Content-Type': 'application/json' })
      expect(JSON.parse(options.body)).toEqual(booking)
    })

    it.each([0, -1, 1.5, null, undefined, '4'])('rejects invalid advisor ID %s', async (id) => {
      await expect(bookMeeting(id, booking)).rejects.toThrow(
        'advisorId must be a positive integer.',
      )
      expect(fetch).not.toHaveBeenCalled()
    })

    it('shows the API message for conflicts', async () => {
      fetch.mockResolvedValue({
        ok: false,
        status: 409,
        json: async () => ({ detail: "This email can't be used to book with this advisor." }),
      })

      await expect(bookMeeting(4, booking)).rejects.toMatchObject({
        message: "This email can't be used to book with this advisor.",
        status: 409,
      })
    })

    it.each([
      [404, 'not accepting bookings'],
      [422, 'check your details'],
      [502, 'Google Meet'],
      [500, 'Unable to book the meeting'],
    ])('uses a friendly message for status %s', async (status, message) => {
      fetch.mockResolvedValue({ ok: false, status, json: async () => ({}) })

      await expect(bookMeeting(4, booking)).rejects.toThrow(message)
    })

    it('falls back when a conflict has no readable message', async () => {
      fetch.mockResolvedValue({
        ok: false,
        status: 409,
        json: async () => {
          throw new Error('not json')
        },
      })

      await expect(bookMeeting(4, booking)).rejects.toThrow('Unable to book the meeting')
    })
  })

  describe('toBookingStart', () => {
    it('uses the Eastern standard time offset in winter', () => {
      expect(toBookingStart(new Date(2026, 10, 19), '10:30 AM')).toBe('2026-11-19T10:30:00-05:00')
    })

    it('uses the Eastern daylight time offset in summer', () => {
      expect(toBookingStart(new Date(2026, 6, 2), '01:30 PM')).toBe('2026-07-02T13:30:00-04:00')
    })

    it('handles noon and midnight', () => {
      expect(toBookingStart(new Date(2026, 10, 19), '12:00 PM')).toBe('2026-11-19T12:00:00-05:00')
      expect(toBookingStart(new Date(2026, 10, 19), '12:15 AM')).toBe('2026-11-19T00:15:00-05:00')
    })

    it('uses the offset in effect after daylight saving time starts', () => {
      // Clocks moved forward at 2 AM on March 8, 2026
      expect(toBookingStart(new Date(2026, 2, 8), '09:30 AM')).toBe('2026-03-08T09:30:00-04:00')
    })

    it('can use another time zone', () => {
      expect(toBookingStart(new Date(2026, 10, 19), '09:00 AM', 'UTC')).toBe(
        '2026-11-19T09:00:00+00:00',
      )
    })

    it.each([
      [undefined, '10:30 AM'],
      [new Date('invalid'), '10:30 AM'],
      [new Date(2026, 10, 19), null],
      [new Date(2026, 10, 19), '25 o clock'],
    ])('rejects an invalid date or time', (date, time) => {
      expect(() => toBookingStart(date, time)).toThrow('A valid date and time are required.')
    })
  })
})
