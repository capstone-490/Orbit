//Above 50% AI generated

export const mapAppointment = (appointmentData) => {
  // Determine when the appointment starts
  const startDate = new Date(
    appointmentData.start ?? appointmentData.meeting_date,
  );

  // Use the provided end date or calculate it from the duration
  const endDate = appointmentData.end
    ? new Date(appointmentData.end)
    : new Date(
        startDate.getTime() + (appointmentData.duration_minutes ?? 60) * 60000,
      );

  // Calculate the total appointment duration in minutes
  const durationMinutes = Math.round((endDate - startDate) / 60000);
  // Return a standardized appointment object for the calendar
  return {
    id: String(
      appointmentData.id ??
        appointmentData.meeting_id ??
        appointmentData.event_id,
    ),
    meetingId: Number.isInteger(
      appointmentData.id ?? appointmentData.meeting_id,
    )
      ? (appointmentData.id ?? appointmentData.meeting_id)
      : null,
    status: appointmentData.completion_status ?? null,
    title: appointmentData.title ?? "",
    kind: appointmentData.kind ?? "session",
    typeId: appointmentData.typeId ?? appointmentData.type_id ?? null,
    client: appointmentData.client ?? appointmentData.client_name ?? "",
    start: startDate,
    end: endDate,
    minutes: durationMinutes,
    meetUrl: appointmentData.meetUrl ?? appointmentData.meeting_uri ?? null,
    source: appointmentData.source ?? "orbit",
  };
};
