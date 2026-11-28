function ClientOverview({ client }) {
  const details = [
    ['Email', client.email],
    ['Phone number', client.phone_number],
    ['Address', client.address],
    ['Age', client.age == null ? null : `${client.age} years`],
    ['Occupation', client.occupation],
    ['Planning stage', client.timeline],
  ]
  const financialSummary = [
    [
      'Annual income',
      client.annual_income == null
        ? null
        : Number(client.annual_income).toLocaleString(),
    ],
    ['Risk tolerance', client.risk_tolerance],
    [
      'Target retirement age',
      client.target_retirement_age == null
        ? null
        : `${client.target_retirement_age} years`,
    ],
  ]

  return (
    <>
      <h2 id="personal-information-title">Personal Information</h2>
      <dl className="client-profile-details">
        {details.map(([label, value]) => (
          <div className="client-profile-detail" key={label}>
            <dt>{label}</dt>
            <dd>{value || 'Not provided'}</dd>
          </div>
        ))}
      </dl>
      <section className="client-financial-summary" aria-labelledby="financial-summary-title">
        <h2 id="financial-summary-title">Financial summary</h2>
        <dl className="client-profile-details">
          {financialSummary.map(([label, value]) => (
            <div className="client-profile-detail" key={label}>
              <dt>{label}</dt>
              <dd>{value ?? 'Not provided'}</dd>
            </div>
          ))}
        </dl>
      </section>
    </>
  )
}

export default ClientOverview
