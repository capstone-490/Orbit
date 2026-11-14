//Above 50% AI generated

import { mock } from "./CalendarMock";
import { mapAppointment } from "./Appointment.mapper";
import { getAdvisorMeetings } from "./MeetingApi";

const BASE = import.meta.env.VITE_API_URL ?? "http://localhost:8001";
const USE_MOCK = import.meta.env.VITE_USE_MOCK === "true";
const GM = "/google-meet-integration";

async function http(path, opts = {}) {
  const res = await fetch(`${BASE}${path}`, {
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    ...opts,
  });
  if (!res.ok) {
    const body = await res.json().catch(() => null);
    const e = new Error(body?.detail ?? `HTTP ${res.status}`);
    e.status = res.status;
    e.detail = body?.detail;
    throw e;
  }
  return res.status === 204 ? null : res.json();
}

const real = {
  async getAppointments(from, to, { advisorId } = {}) {
    const rows = await getAdvisorMeetings(advisorId);
    return rows.filter((r) => {
      const s = new Date(r.meeting_date);
      return s >= from && s < to;
    });
  },
  createAppointment: ({ clientId, title, start, minutes }) =>
    http(`${GM}/meetings`, {
      method: "POST",
      body: JSON.stringify({
        client_id: clientId,
        title,
        start: start.toISOString(),
        duration_minutes: minutes,
      }),
    }),
  getGoogleStatus: () => http(`${GM}/status`),
};

const source = USE_MOCK ? mock : real;

export const calendarApi = {
  ...source,
  getAppointments: async (from, to, opts) =>
    (await source.getAppointments(from, to, opts)).map(mapAppointment),
  createAppointment: async (payload) =>
    mapAppointment(await source.createAppointment(payload)),
  connectUrl: `${BASE}${GM}/authorize`,
};
