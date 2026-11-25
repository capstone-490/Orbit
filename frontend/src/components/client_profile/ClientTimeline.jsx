function ClientTimeline({ client }) {
  return (
    <section className="client-profile-empty" aria-labelledby="client-timeline-heading">
      <h2 id="client-timeline-heading">Client timeline</h2>
      <p>Planning stage: {client.timeline || 'Not provided'}</p>
      <p>Client activity will appear here as it is recorded.</p>
    </section>
  )
}

export default ClientTimeline
