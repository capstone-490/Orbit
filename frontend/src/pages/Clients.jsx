// Substantial AI assistance used; verified with frontend tests and production build.
import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import ClientFormModal from '../components/client_profile/ClientFormModal'
import { isValidPhoneNumber } from '../components/client_profile/clientProfileValidation'
import { API_BASE_URL, withAuthCredentials } from '../services/AuthApi'
import '../styles/Clients.css'

function Clients() {
  const [search, setSearch] = useState('')
  const [clients, setClients] = useState([])
  const [loading, setLoading] = useState(true)
  const [loadError, setLoadError] = useState('')
  const [formError, setFormError] = useState('')
  const [success, setSuccess] = useState('')
  const [saving, setSaving] = useState(false)
  const [showAddClient, setShowAddClient] = useState(false)

  useEffect(() => {
    let active = true
    const fetchClients = async () => {
      try {
        const response = await fetch(`${API_BASE_URL}/clients`, withAuthCredentials())
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

  const closeModal = () => {
    if (saving) return
    setShowAddClient(false)
    setFormError('')
  }

  const handleAddClient = async (formValues) => {
    if (saving) return
    setFormError('')
    setSuccess('')

    if (!isValidPhoneNumber(formValues.phone_number)) {
      setFormError('Please enter a valid Canadian or US phone number.')
      return
    }

    setSaving(true)

    const payload = {
      name: formValues.name,
      email: formValues.email,
      phone_number: formValues.phone_number,
      address: formValues.address || null,
      date_of_birth: formValues.date_of_birth || null,
      occupation: formValues.occupation || null,
      timeline: formValues.timeline || null,
      annual_income: formValues.annual_income ?? null,
      risk_tolerance: formValues.risk_tolerance || null,
      target_retirement_age: formValues.target_retirement_age ?? null,
    }

    try {
      const response = await fetch(
        `${API_BASE_URL}/clients`,
        withAuthCredentials({
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload),
        }),
      )
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
        const listResponse = await fetch(`${API_BASE_URL}/clients`, withAuthCredentials())
        if (!listResponse.ok) throw new Error('Refresh failed')
        setClients(await listResponse.json())
        setLoadError('')
      } catch {
        setLoadError('Client saved, but the list could not be refreshed. Reload the page.')
      }

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

              <Link
                className="client-arrow"
                to={`/clients/${client.id}`}
                aria-label={`View ${client.name} information`}
              >
                <span aria-hidden="true">›</span>
              </Link>
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

      {showAddClient && (
        <ClientFormModal
          mode="add"
          error={formError}
          onClose={closeModal}
          onSubmit={handleAddClient}
          saving={saving}
        />
      )}
    </main>
  )
}

export default Clients
