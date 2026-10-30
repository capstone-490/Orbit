import { useEffect, useState } from 'react'
import '../styles/Clients.css'

const API_URL = 'http://localhost:8001'

const isValidPhoneNumber = (value) => {
  const phone = value.trim()

  if (!/^\+?[\d\s().-]+$/.test(phone)) return false

  let digits = phone.replace(/\D/g, '')

  if (digits.length === 11 && digits.startsWith('1')) {
    digits = digits.slice(1)
  }

  return digits.length === 10 && /^[2-9]\d{2}[2-9]\d{6}$/.test(digits)
}
const emptyClient = {
  name: '',
  email: '',
  phone_number: '',
  address: '',
  date_of_birth: '',
  occupation: '',
  timeline: '',
}

function Clients() {
  const [search, setSearch] = useState('')
  const [clients, setClients] = useState([])
  const [loading, setLoading] = useState(true)
  const [loadError, setLoadError] = useState('')
  const [formError, setFormError] = useState('')
  const [success, setSuccess] = useState('')
  const [saving, setSaving] = useState(false)
  const [showAddClient, setShowAddClient] = useState(false)
  const [newClient, setNewClient] = useState({ ...emptyClient })

  useEffect(() => {
    let active = true
    const fetchClients = async () => {
      try {
        const response = await fetch(`${API_URL}/clients`)
        if (!response.ok) throw new Error('Failed to load clients.')
        const data = await response.json()
        if (active) setClients(data)
      } catch (error) {
        if (active) setLoadError(error.message)
      } finally {
        if (active) setLoading(false)
      }
    }
    void fetchClients()
    return () => {
      active = false
    }
  }, [])

  useEffect(() => {
    if (!success) return

    const timer = setTimeout(() => {
      setSuccess('')
    }, 3000)

    return () => clearTimeout(timer)
  }, [success])

  const filteredClients = clients.filter((client) => {
    const term = search.trim().toLowerCase()
    return client.name.toLowerCase().includes(term) || client.email.toLowerCase().includes(term)
  })

  const handleClientChange = (e) => {
    const { name, value } = e.target
    setNewClient((prev) => ({ ...prev, [name]: value }))
  }

  const closeModal = () => {
    if (saving) return
    setShowAddClient(false)
    setFormError('')
  }

  const handleAddClient = async (e) => {
    e.preventDefault()
    if (saving) return
    setFormError('')
    setSuccess('')

    if (!isValidPhoneNumber(newClient.phone_number)) {
      setFormError('Please enter a valid Canadian or US phone number.')
      return
    }

    setSaving(true)

    const payload = {
      name: newClient.name.trim(),
      email: newClient.email.trim(),
      phone_number: newClient.phone_number.trim(),
      address: newClient.address.trim() || null,
      date_of_birth: newClient.date_of_birth || null,
      occupation: newClient.occupation.trim() || null,
      timeline: newClient.timeline || null,
    }

    try {
      const response = await fetch(`${API_URL}/clients`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      })
      if (!response.ok) {
        const details = await response.json().catch(() => ({}))
        throw new Error(
          typeof details.detail === 'string'
            ? details.detail
            : 'Failed to add client. Please check the entered information.',
        )
      }

      const created = await response.json()
      // Re-fetch so the list always reflects the database.
      try {
        const listResponse = await fetch(`${API_URL}/clients`)
        if (!listResponse.ok) throw new Error('Refresh failed')
        setClients(await listResponse.json())
        setLoadError('')
      } catch {
        setLoadError('Client saved, but the list could not be refreshed. Reload the page.')
      }

      setNewClient({ ...emptyClient })
      setShowAddClient(false)
      setSuccess(`Client saved successfully (ID: ${created.id}).`)
    } catch (error) {
      setFormError(error.message)
    } finally {
      setSaving(false)
    }
  }

  return (
    <main className="clients-page">
      <div className="clients-header">
        <h1>Clients</h1>

        {/* Add Client functionality */}
        <button
          type="button"
          className="add-client-button"
          onClick={() => {
            setFormError('')
            setSuccess('')
            setShowAddClient(true)
          }}
        >
          + Add Client
        </button>
      </div>

      <div className="clients-toolbar">
        <div className="clients-search">
          <span aria-hidden="true">⌕</span>
          <input
            type="search"
            placeholder="Search clients by name or email..."
            aria-label="Search clients"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>

        <div className="clients-filters">
          <span className="filter-button selected">All Clients ({clients.length})</span>
        </div>
      </div>

      {loading && <p role="status">Loading clients...</p>}
      {loadError && (
        <p className="clients-error" role="alert">
          {loadError}
        </p>
      )}
      {success && (
        <p role="status" style={{ color: '#166534' }}>
          {success}
        </p>
      )}

      <section className="clients-list">
        {!loading && !loadError && filteredClients.length > 0 ? (
          filteredClients.map((client) => (
            <div className="client-row" key={client.id}>
              <div className="client-info">
                <div className="client-avatar">
                  {client.name
                    .trim()
                    .split(/\s+/)
                    .map((part) => part[0])
                    .slice(0, 2)
                    .join('')
                    .toUpperCase()}
                </div>

                <div className="client-details">
                  <h3>{client.name}</h3>
                  <p>{client.email}</p>
                </div>
              </div>

              <div className="client-meeting">
                <span>No upcoming meeting</span>
              </div>

              {/* Client profile navigation will be added later */}
              <span className="client-arrow" aria-hidden="true">
                ›
              </span>
            </div>
          ))
        ) : (
          <div className="clients-empty">
            {loading
              ? 'Loading clients...'
              : loadError
                ? 'Unable to display clients.'
                : 'No clients found.'}
          </div>
        )}
      </section>

      {/* Add Client Modal */}
      {showAddClient && (
        <div className="client-modal-overlay">
          <button
            type="button"
            className="client-modal-backdrop"
            aria-label="Close Add Client form"
            onClick={closeModal}
            disabled={saving}
          />
          <div
            className="client-modal"
            role="dialog"
            aria-modal="true"
            aria-labelledby="add-client-title"
          >
            <div className="client-modal-header">
              <h2 id="add-client-title">Add New Client</h2>

              <button
                type="button"
                className="client-modal-close"
                aria-label="Close form"
                onClick={closeModal}
                disabled={saving}
              >
                ×
              </button>
            </div>

            <form onSubmit={handleAddClient}>
              {formError && (
                <p className="clients-error" role="alert" style={{ color: '#dc2626' }}>
                  {formError}
                </p>
              )}
              <div className="client-form-grid">
                <label>
                  Full Name *
                  <input
                    type="text"
                    name="name"
                    value={newClient.name}
                    onChange={handleClientChange}
                    required
                  />
                </label>

                <label>
                  Email *
                  <input
                    type="email"
                    name="email"
                    value={newClient.email}
                    onChange={handleClientChange}
                    required
                  />
                </label>

                <label>
                  Phone Number *
                  <input
                    type="tel"
                    name="phone_number"
                    value={newClient.phone_number}
                    onChange={handleClientChange}
                    required
                  />
                </label>

                <label>
                  Address
                  <input
                    type="text"
                    name="address"
                    value={newClient.address}
                    onChange={handleClientChange}
                  />
                </label>

                <label>
                  Date of Birth (used to calculate age)
                  <input
                    type="date"
                    name="date_of_birth"
                    value={newClient.date_of_birth}
                    onChange={handleClientChange}
                  />
                </label>

                <label>
                  Occupation
                  <input
                    type="text"
                    name="occupation"
                    value={newClient.occupation}
                    onChange={handleClientChange}
                  />
                </label>

                <label className="client-form-full">
                  Timeline
                  <select name="timeline" value={newClient.timeline} onChange={handleClientChange}>
                    <option value="">Select current stage</option>
                    <option value="Corporate Introduction">Corporate Introduction</option>
                    <option value="Investment Education">Investment Education</option>
                    <option value="Tax Education">Tax Education</option>
                    <option value="Insurance Education">Insurance Education</option>
                    <option value="Financial Needs Analysis">Financial Needs Analysis</option>
                    <option value="Financial Plan">Financial Plan</option>
                  </select>
                </label>
              </div>

              <div className="client-modal-actions">
                <button type="button" className="client-cancel-button" onClick={closeModal}>
                  Cancel
                </button>

                <button type="submit" className="client-save-button">
                  Save Client
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </main>
  )
}

export default Clients
