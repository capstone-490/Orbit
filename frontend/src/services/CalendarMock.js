//Above 50% AI generated

import { SESSION_TYPES } from '../constants/sessionTypes'

const delay = (ms = 400) => new Promise((r) => setTimeout(r, ms))
const at = (dayOffset, h, m = 0) => {
  const d = new Date()
  d.setHours(h, m, 0, 0)
  d.setDate(d.getDate() + dayOffset)
  return d
}
const iso = (d) => d.toISOString()
const plus = (d, minutes) => new Date(d.getTime() + minutes * 60000)

const session = (id, client, typeId, start, minutes = 60) => ({
  id,
  client_name: client,
  type_id: typeId,
  title: SESSION_TYPES[typeId]?.label ?? 'Meeting',
  meeting_date: iso(start),
  duration_minutes: minutes,
  completion_status: 'Scheduled',
  meeting_uri: 'https://meet.google.com/abc-defg-hij',
})

// Busy blocks have no title or client
const busy = (id, start, minutes) => ({
  id,
  kind: 'busy',
  start: iso(start),
  end: iso(plus(start, minutes)),
  source: 'google',
})

const startOf = (a) => new Date(a.meeting_date ?? a.start)

let appointments = [
  session('evt_1', 'Noah Lee', 'tax', at(0, 15, 30)),
  session('evt_2', 'John Lee', 'introduction', at(1, 16, 30)),
  busy('g_1', at(2, 10), 60), // "Dentist Appointment" as Busy
  session('evt_3', 'Eleanor Lee', 'planning', at(3, 14)), // overlaps the next one
  session('evt_4', 'Marcus Lee', 'investment', at(3, 14, 30)),
  session('evt_5', 'Adam Lee', 'investment', at(4, 17, 30), 90), // non-60-minute duration
  session('evt_6', 'Janet Lee', 'type_not_in_constants', at(-3, 10)), // unknown type: tests the fallback
  busy('g_2', at(0, 12, 30), 60),
]

export const mock = {
  async getAppointments(from, to, { signal } = {}) {
    await delay()
    if (signal?.aborted) throw new DOMException('Aborted', 'AbortError')
    return appointments.filter((a) => {
      const s = startOf(a)
      return s >= from && s < to
    })
  },

  async createAppointment({ title, start, minutes }) {
    await delay(300)
    const created = {
      ...session(`evt_${Date.now()}`, 'New client', null, new Date(start), minutes),
      title,
    }
    appointments = [...appointments, created]
    return created
  },

  async getGoogleStatus() {
    await delay(150)
    return { connected: true }
  },
}
