
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { API_BASE_URL } from '../services/AuthApi'
import { createClientNote, getClientNotes } from '../services/NotesApi'

const notePayload = {
  title: 'Investment discussion',
  content: 'Discussed investment goals.',
}

const savedNote = {
  id: 1,
  ...notePayload,
  client_id: 1,
  author_id: 1,
  author_type: 'Advisor',
  created_at: '2026-11-27T12:00:00Z',
  updated_at: '2026-11-27T12:00:00Z',
}

describe('NotesApi', () => {
  beforeEach(() => {
    vi.stubGlobal('fetch', vi.fn())
  })

  afterEach(() => {
    vi.unstubAllGlobals()
  })

  describe('getClientNotes', () => {
    it('retrieves client notes with credentials', async () => {
      fetch.mockResolvedValue({
        ok: true,
        json: async () => [savedNote],
      })

      await expect(getClientNotes(1)).resolves.toEqual([savedNote])

      expect(fetch).toHaveBeenCalledWith(
        `${API_BASE_URL}/clients/1/notes`,
        { credentials: 'include' },
      )
    })

    it('returns an empty array when no notes exist', async () => {
      fetch.mockResolvedValue({
        ok: true,
        json: async () => [],
      })

      await expect(getClientNotes(1)).resolves.toEqual([])
    })

    it.each([401, 403, 404, 500])(
      'throws when loading notes fails with status %s',
      async (status) => {
        fetch.mockResolvedValue({
          ok: false,
          status,
        })

        await expect(getClientNotes(1)).rejects.toThrow(
          'Unable to load client notes.',
        )
      },
    )

    it('propagates network failures', async () => {
      fetch.mockRejectedValue(new TypeError('Network unavailable'))

      await expect(getClientNotes(1)).rejects.toThrow(
        'Network unavailable',
      )
    })
  })

  describe('createClientNote', () => {
    it('sends a POST request with the note payload', async () => {
      fetch.mockResolvedValue({
        ok: true,
        status: 201,
        json: async () => savedNote,
      })

      await expect(
        createClientNote(1, notePayload),
      ).resolves.toEqual(savedNote)

      expect(fetch).toHaveBeenCalledWith(
        `${API_BASE_URL}/clients/1/notes`,
        {
          method: 'POST',
          credentials: 'include',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify(notePayload),
        },
      )
    })

    it.each([401, 403, 404, 422, 500])(
      'throws when creating a note fails with status %s',
      async (status) => {
        fetch.mockResolvedValue({
          ok: false,
          status,
        })

        await expect(
          createClientNote(1, notePayload),
        ).rejects.toThrow('Unable to create client note.')
      },
    )

    it('propagates network failures', async () => {
      fetch.mockRejectedValue(new TypeError('Network unavailable'))

      await expect(
        createClientNote(1, notePayload),
      ).rejects.toThrow('Network unavailable')
    })
  })
})
