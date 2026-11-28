import { useState } from 'react'

const emptyClient = {
  name: '',
  email: '',
  phone_number: '',
  address: '',
  date_of_birth: '',
  occupation: '',
  timeline: '',
  annual_income: '',
  risk_tolerance: '',
  target_retirement_age: '',
}

function ClientFormModal({ client, error, mode, onClose, onSubmit, saving }) {
  const [values, setValues] = useState({ ...emptyClient })
  const isEditing = mode === 'edit'

  const handleChange = (event) => {
    const { name, value } = event.target
    setValues((current) => ({ ...current, [name]: value }))
  }

  const handleSubmit = (event) => {
    event.preventDefault()

    const submittedValues = Object.fromEntries(
      Object.entries(values)
        .filter(([, value]) => value.trim() !== '')
        .map(([key, value]) => [
          key,
          ['annual_income', 'target_retirement_age'].includes(key)
            ? Number(value)
            : ['name', 'email', 'phone_number', 'address', 'occupation'].includes(key)
              ? value.trim()
              : value,
        ]),
    )

    onSubmit(submittedValues)
  }

  return (
    <div className="client-modal-overlay">
      <button
        type="button"
        className="client-modal-backdrop"
        aria-label={`Close ${isEditing ? 'Edit' : 'Add'} Client form`}
        onClick={onClose}
        disabled={saving}
      />
      <div
        className="client-modal"
        role="dialog"
        aria-modal="true"
        aria-labelledby="client-form-title"
      >
        <div className="client-modal-header">
          <h2 id="client-form-title">{isEditing ? 'Edit Client Profile' : 'Add New Client'}</h2>
          <button
            type="button"
            className="client-modal-close"
            aria-label="Close form"
            onClick={onClose}
            disabled={saving}
          >
            ×
          </button>
        </div>

        <form onSubmit={handleSubmit}>
          {error && (
            <p className="clients-error" role="alert" style={{ color: '#dc2626' }}>
              {error}
            </p>
          )}
          <div className="client-form-grid">
            <label>
              Full Name {isEditing ? '' : '*'}
              <input
                type="text"
                name="name"
                value={values.name}
                placeholder={isEditing ? client.name : ''}
                onChange={handleChange}
                required={!isEditing}
              />
            </label>

            <label>
              Email {isEditing ? '' : '*'}
              <input
                type="email"
                name="email"
                value={values.email}
                placeholder={isEditing ? client.email : ''}
                onChange={handleChange}
                required={!isEditing}
              />
            </label>

            <label>
              Phone Number {isEditing ? '' : '*'}
              <input
                type="tel"
                name="phone_number"
                value={values.phone_number}
                placeholder={isEditing ? client.phone_number : ''}
                onChange={handleChange}
                required={!isEditing}
              />
            </label>

            <label>
              Address
              <input
                type="text"
                name="address"
                value={values.address}
                placeholder={isEditing ? client.address || 'Not provided' : ''}
                onChange={handleChange}
              />
            </label>

            <label>
              Date of Birth (used to calculate age)
              {isEditing && (
                <span className="client-form-hint">
                  Current age: {client.age == null ? 'not provided' : `${client.age} years`}. Date
                  of birth is not stored.
                </span>
              )}
              <input
                type="date"
                name="date_of_birth"
                value={values.date_of_birth}
                max={isEditing ? new Date().toISOString().slice(0, 10) : undefined}
                onChange={handleChange}
              />
            </label>

            <label>
              Occupation
              <input
                type="text"
                name="occupation"
                value={values.occupation}
                placeholder={isEditing ? client.occupation || 'Not provided' : ''}
                onChange={handleChange}
              />
            </label>

            <label className="client-form-full">
              Timeline
              <select name="timeline" value={values.timeline} onChange={handleChange}>
                <option value="">
                  {isEditing ? client.timeline || 'Not provided' : 'Select current stage'}
                </option>
                <option value="Corporate Introduction">Corporate Introduction</option>
                <option value="Investment Education">Investment Education</option>
                <option value="Tax Education">Tax Education</option>
                <option value="Insurance Education">Insurance Education</option>
                <option value="Financial Needs Analysis">Financial Needs Analysis</option>
                <option value="Financial Plan">Financial Plan</option>
              </select>
            </label>

            <label>
              Annual income
              <input
                type="number"
                name="annual_income"
                min="0"
                step="0.01"
                value={values.annual_income}
                placeholder={isEditing ? client.annual_income ?? 'Not provided' : ''}
                onChange={handleChange}
              />
            </label>

            <label>
              Risk tolerance
              <select
                name="risk_tolerance"
                value={values.risk_tolerance}
                onChange={handleChange}
              >
                <option value="">
                  {isEditing ? client.risk_tolerance || 'Not provided' : 'Select risk tolerance'}
                </option>
                <option value="Conservative">Conservative</option>
                <option value="Moderate">Moderate</option>
                <option value="Aggressive">Aggressive</option>
              </select>
            </label>

            <label>
              Target retirement age
              <input
                type="number"
                name="target_retirement_age"
                min="0"
                max="130"
                step="1"
                value={values.target_retirement_age}
                placeholder={
                  isEditing ? client.target_retirement_age ?? 'Not provided' : ''
                }
                onChange={handleChange}
              />
            </label>
          </div>

          <div className="client-modal-actions">
            <button
              type="button"
              className="client-cancel-button"
              onClick={onClose}
              disabled={saving}
            >
              Cancel
            </button>
            <button type="submit" className="client-save-button" disabled={saving}>
              {saving ? 'Saving...' : isEditing ? 'Save Changes' : 'Save Client'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

export default ClientFormModal
