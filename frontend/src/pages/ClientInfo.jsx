import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import ClientDocuments from '../components/client_profile/ClientDocuments'
import ClientFormModal from '../components/client_profile/ClientFormModal'
import ClientMeetings from '../components/client_profile/ClientMeetings'
import ClientOverview from '../components/client_profile/ClientOverview'
import ClientTask from '../components/client_profile/ClientTask'
import ClientTimeline from '../components/client_profile/ClientTimeline'
import ClientSnapshot from '../components/client_profile/ClientSnapshot'
import { isValidPhoneNumber } from '../components/client_profile/clientProfileValidation'
import { API_BASE_URL, withAuthCredentials } from '../services/AuthApi'
import '../styles/Clients.css'

function ClientInfo() {
  const { clientId } = useParams()
  const [activeTab, setActiveTab] = useState('overview')
  const [client, setClient] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [formError, setFormError] = useState('')
  const [saving, setSaving] = useState(false)
  const [editing, setEditing] = useState(false)
  const [success, setSuccess] = useState('')

  const tabs = [
    { id: 'overview', label: 'Overview', component: ClientOverview },
    { id: 'timeline', label: 'Timeline', component: ClientTimeline },
    { id: 'financial-snapshot', label: 'Financial Snapshot', component: ClientSnapshot },
    { id: 'tasks', label: 'Tasks', component: ClientTask },
    { id: 'meetings', label: 'Meetings', component: ClientMeetings },
    { id: 'documents', label: 'Documents', component: ClientDocuments },
  ]

  useEffect(() => {
    let active = true

    const fetchClient = async () => {
      try {
        const response = await fetch(`${API_BASE_URL}/clients/${clientId}`, withAuthCredentials())
        if (!response.ok) {
          throw new Error(
            response.status === 404 ? 'Client not found.' : 'Unable to load client information.',
          )
        }

        const data = await response.json()
        if (active) setClient(data)
      } catch (fetchError) {
        if (active) setError(fetchError.message)
      } finally {
        if (active) setLoading(false)
      }
    }

    void fetchClient()
    return () => {
      active = false
    }
  }, [clientId])

  const closeEditModal = () => {
    if (saving) return
    setEditing(false)
    setFormError('')
  }

  const handleUpdateClient = async (values) => {
    if (saving) return
    setFormError('')
    setSuccess('')

    if (Object.keys(values).length === 0) {
      setFormError('Enter at least one profile change before saving.')
      return
    }

    if (values.phone_number && !isValidPhoneNumber(values.phone_number)) {
      setFormError('Please enter a valid Canadian or US phone number.')
      return
    }

    const payload = { ...values }
    if (payload.date_of_birth) {
      const birthDate = new Date(`${payload.date_of_birth}T00:00:00`)
      const today = new Date()
      if (birthDate > today) {
        setFormError('Date of birth cannot be in the future.')
        return
      }

      const hasHadBirthdayThisYear =
        today.getMonth() > birthDate.getMonth() ||
        (today.getMonth() === birthDate.getMonth() && today.getDate() >= birthDate.getDate())
      payload.age = today.getFullYear() - birthDate.getFullYear() - (hasHadBirthdayThisYear ? 0 : 1)
      delete payload.date_of_birth
    }

    setSaving(true)
    try {
      const response = await fetch(
        `${API_BASE_URL}/clients/${clientId}`,
        withAuthCredentials({
          method: 'PATCH',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload),
        }),
      )

      if (!response.ok) {
        const details = await response.json().catch(() => ({}))
        throw new Error(
          typeof details.detail === 'string'
            ? details.detail
            : 'Unable to update client information.',
        )
      }

      const updatedClient = await response.json()
      setClient((current) => ({ ...current, ...updatedClient }))
      setEditing(false)
      setSuccess('Client profile updated successfully.')
    } catch (updateError) {
      setFormError(updateError.message)
    } finally {
      setSaving(false)
    }
  }

  if (loading) {
    return (
      <main className="client-info-page">
        <p role="status">Loading client information...</p>
      </main>
    )
  }

  if (error) {
    return (
      <main className="client-info-page">
        <Link className="client-info-back" to="/clients">
          Back to clients
        </Link>
        <p className="clients-error" role="alert">
          {error}
        </p>
      </main>
    )
  }

  const initials = client.name
    .trim()
    .split(/\s+/)
    .map((part) => part[0])
    .slice(0, 2)
    .join('')
    .toUpperCase()

  const ActiveTab = tabs.find((tab) => tab.id === activeTab)?.component ?? ClientOverview

  return (
    <main className="client-info-page">
      <Link className="client-info-back" to="/clients">
        ‹ Back to clients
      </Link>

      <section className="client-info-card" aria-labelledby="client-info-title">
        {success && (
          <p role="status" className="client-profile-success">
            {success}
          </p>
        )}
        <div className="client-info-header">
          <div className="client-avatar client-info-avatar" aria-hidden="true">
            {initials}
          </div>
          <div>
            <p className="client-info-eyebrow">Client profile</p>
            <h1 id="client-info-title">{client.name}</h1>
          </div>
          <button
            type="button"
            className="client-info-edit"
            onClick={() => {
              setFormError('')
              setSuccess('')
              setEditing(true)
            }}
          >
            Edit profile
          </button>
        </div>

        <div className="client-profile-tabs" role="tablist" aria-label="Client profile sections">
          {tabs.map(({ id, label }) => (
            <button
              type="button"
              className="client-profile-tab"
              id={`client-profile-tab-${id}`}
              role="tab"
              aria-selected={activeTab === id}
              aria-controls="client-profile-panel"
              tabIndex={activeTab === id ? 0 : -1}
              key={id}
              onClick={() => setActiveTab(id)}
              onKeyDown={(event) => {
                const currentIndex = tabs.findIndex((tab) => tab.id === activeTab)
                let nextIndex

                if (event.key === 'ArrowRight') nextIndex = (currentIndex + 1) % tabs.length
                else if (event.key === 'ArrowLeft')
                  nextIndex = (currentIndex - 1 + tabs.length) % tabs.length
                else if (event.key === 'Home') nextIndex = 0
                else if (event.key === 'End') nextIndex = tabs.length - 1
                else return

                event.preventDefault()
                setActiveTab(tabs[nextIndex].id)
                document.getElementById(`client-profile-tab-${tabs[nextIndex].id}`)?.focus()
              }}
            >
              {label}
            </button>
          ))}
        </div>

        <div
          className="client-profile-panel"
          id="client-profile-panel"
          role="tabpanel"
          aria-labelledby={`client-profile-tab-${activeTab}`}
        >
          <ActiveTab client={client} clientId={client.id} />
        </div>
      </section>
      {editing && (
        <ClientFormModal
          mode="edit"
          client={client}
          error={formError}
          onClose={closeEditModal}
          onSubmit={handleUpdateClient}
          saving={saving}
        />
      )}
    </main>
  )
}

export default ClientInfo
