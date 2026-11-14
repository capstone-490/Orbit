//Above 50% AI generated

import { mapAppointment } from "../../services/Appointment.mapper";
import { mock } from "../../services/CalendarMock";

/**
 * Tests for mapping appointment data into the calendar format.
 */

describe("mapAppointment", () => {
  it("converts appointment start and end strings into Date objects and calculates the duration", () => {
    const appointment = mapAppointment({
      id: "1",
      start: "2026-11-13T21:00:00Z",
      end: "2026-11-13T22:30:00Z",
    });
    expect(appointment.start).toBeInstanceOf(Date);
    expect(appointment.minutes).toBe(90);
  });

  it("assigns default values when optional appointment fields are missing", () => {
    const appointment = mapAppointment({
      id: "1",
      start: "2026-11-13T21:00:00Z",
      end: "2026-11-13T22:00:00Z",
    });
    expect(appointment).toMatchObject({
      kind: "session",
      client: "",
      meetUrl: null,
      source: "orbit",
    });
  });
  it("maps a backend meeting response to the expected appointment format", () => {
    const appointment = mapAppointment({
      id: 7,
      client_id: 3,
      advisor_id: 1,
      client_name: "Ann",
      meeting_date: "2026-11-13T21:00:00Z",
      duration_minutes: 45,
      completion_status: "Scheduled",
      meeting_uri: "https://meet.google.com/x",
      meeting_code: "abc-defg-hij",
    });
    expect(appointment).toMatchObject({
      id: "7",
      meetingId: 7,
      status: "Scheduled",
      client: "Ann",
      minutes: 45,
      meetUrl: "https://meet.google.com/x",
      kind: "session",
      title: "",
    });
    expect(appointment.start).toBeInstanceOf(Date);
  });

  it("uses default duration and meeting URL when the backend response omits them", () => {
    const appointment = mapAppointment({
      id: 8,
      client_name: "Bob",
      meeting_date: "2026-11-13T21:00:00Z",
      completion_status: "Completed",
    });
    expect(appointment.minutes).toBe(60);
    expect(appointment.meetUrl).toBeNull();
    expect(appointment.status).toBe("Completed");
  });

  it("maps busy calendar blocks without assigning a meeting ID", () => {
    const appointment = mapAppointment({
      id: "g_1",
      kind: "busy",
      start: "2026-11-13T21:00:00Z",
      end: "2026-11-13T22:00:00Z",
      source: "google",
    });
    expect(appointment.meetingId).toBeNull();
    expect(appointment.kind).toBe("busy");
  });
});

describe("CalendarMock", () => {
  it("returns valid appointment ranges and busy blocks without client information", async () => {
    const from = new Date(Date.now() - 30 * 864e5),
      to = new Date(Date.now() + 30 * 864e5);
    const appointments = (await mock.getAppointments(from, to)).map(
      mapAppointment,
    );
    // The mock should return at least one appointment.
    expect(appointments.length).toBeGreaterThan(0);
    appointments.forEach((appointment) => {
      expect(appointment.end > appointment.start).toBe(true);
      if (appointment.kind === "busy") expect(appointment.client).toBe("");
    });
  });
});
