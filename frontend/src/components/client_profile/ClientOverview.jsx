function ClientOverview({ client }) {
  const details = [
    ['Email', client.email],
    ['Phone number', client.phone_number],
    ['Address', client.address],
    ['Age', client.age == null ? null : `${client.age} years`],
    ['Occupation', client.occupation],
    ['Planning stage', client.timeline],
  ]

  return (
    <dl className="client-profile-details">
      {details.map(([label, value]) => (
        <div className="client-profile-detail" key={label}>
          <dt>{label}</dt>
          <dd>{value || 'Not provided'}</dd>
        </div>
      ))}
    </dl>
  )
}

export default ClientOverview
