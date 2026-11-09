//Below 50% AI generated
import { useEffect, useMemo, useState } from 'react'
import { FiAlertTriangle, FiCalendar, FiCheck, FiPlus, FiSearch } from 'react-icons/fi'
import {
  getFollowUps,
  createFollowUp,
  updateFollowUp,
  updateFollowUpStatus,
} from '../services/FollowUpsApi'
import { withAuthCredentials } from '../services/AuthApi'
import '../styles/FollowUps.css'

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8001'

const stages = [
  'Corporate Introduction',
  'Investment Education',
  'Tax Education',
  'Insurance Education',
  'Financial Needs Analysis',
  'Financial Plan',
]
const priorities = ['Low', 'Medium', 'High']
const statuses = ['Pending', 'In Progress', 'Completed', 'Cancelled']
const emptyForm = {
  client_id: '',
  reason: '',
  financial_planning_stage: '',
  due_date: '',
  priority: 'Medium',
  status: 'Pending',
}

function formatDate(value) {
  return new Intl.DateTimeFormat('en-CA', { dateStyle: 'medium' }).format(
    new Date(`${value}T00:00:00`),
  )
}

function getLocalDateKey() {
  const now = new Date()
  const month = String(now.getMonth() + 1).padStart(2, '0')
  const day = String(now.getDate()).padStart(2, '0')
  return `${now.getFullYear()}-${month}-${day}`
}

function stageShortName(stage) {
  return (
    { 'Corporate Introduction': 'Corporate', 'Financial Needs Analysis': 'FNA' }[stage] || stage
  )
}

function FollowUps() {
  const [followUps, setFollowUps] = useState([])
  const [clients, setClients] = useState([])
  const [search, setSearch] = useState('')
  const [filter, setFilter] = useState('All')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [saving, setSaving] = useState(false)
  const [formError, setFormError] = useState('')
  const [isModalOpen, setIsModalOpen] = useState(false)
  const [editing, setEditing] = useState(null)
  const [form, setForm] = useState(emptyForm)

  const clientById = useMemo(() => new Map(clients.map((client) => [client.id, client])), [clients])

  async function loadData() {
    setError('')
    try {
      const [followUpData, clientResponse] = await Promise.all([
        getFollowUps(),
        fetch(`${API_BASE_URL}/clients`, withAuthCredentials()),
      ])
      if (!clientResponse.ok) throw new Error('Unable to load advisor clients.')
      setFollowUps(followUpData)
      setClients(await clientResponse.json())
    } catch (loadError) {
      setError(loadError.message)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    // The effect loads external API data and updates the page state when it resolves.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    void loadData()
  }, [])

  const visibleFollowUps = useMemo(() => {
    const term = search.trim().toLowerCase()
    const today = getLocalDateKey()
    return followUps.filter((followUp) => {
      const client = clientById.get(followUp.client_id)
      const matchesSearch =
        !term ||
        [client?.name, followUp.reason, followUp.financial_planning_stage]
          .filter(Boolean)
          .some((value) => value.toLowerCase().includes(term))
      const matchesFilter =
        filter === 'All' ||
        (filter === 'Overdue' && followUp.status !== 'Completed' && followUp.due_date < today) ||
        (filter === 'Due Today' && followUp.due_date === today) ||
        (filter === 'Upcoming' && followUp.status !== 'Completed' && followUp.due_date > today)
      return matchesSearch && matchesFilter
    })
  }, [clientById, filter, followUps, search])

  const today = getLocalDateKey()
  const overdueCount = followUps.filter(
    (item) => item.status !== 'Completed' && item.due_date < today,
  ).length
  const dueTodayCount = followUps.filter((item) => item.due_date === today).length
  const upcomingCount = followUps.filter(
    (item) => item.status !== 'Completed' && item.due_date > today,
  ).length

  function openCreate() {
    setEditing(null)
    setForm(emptyForm)
    setFormError('')
    setIsModalOpen(true)
  }

  function openEdit(followUp) {
    setEditing(followUp)
    setForm({
      client_id: followUp.client_id,
      reason: followUp.reason,
      financial_planning_stage: followUp.financial_planning_stage,
      due_date: followUp.due_date,
      priority: followUp.priority,
      status: followUp.status,
    })
    setFormError('')
    setIsModalOpen(true)
  }

  async function handleSubmit(event) {
    event.preventDefault()
    setSaving(true)
    setFormError('')
    try {
      const payload = {
        reason: form.reason.trim(),
        financial_planning_stage: form.financial_planning_stage,
        due_date: form.due_date,
        priority: form.priority,
        status: form.status,
      }
      if (editing) {
        await updateFollowUp(editing.id, payload)
      } else {
        await createFollowUp({ ...payload, client_id: Number(form.client_id) })
      }
      setIsModalOpen(false)
      await loadData()
    } catch (saveError) {
      setFormError(saveError.message)
    } finally {
      setSaving(false)
    }
  }

  async function handleStatusChange(followUp, status) {
    try {
      await updateFollowUpStatus(followUp.id, status)
      setFollowUps((current) =>
        current.map((item) => (item.id === followUp.id ? { ...item, status } : item)),
      )
    } catch (statusError) {
      setError(statusError.message)
    }
  }

  return (
    <main className="follow-ups-page">
      <header className="follow-ups-header">
        <div>
          <p className="eyebrow">Advisor workspace</p>
          <h1>Follow-Up Tracker</h1>
          <p>Track Canadian client communications, upcoming follow-ups, and next steps.</p>
        </div>
        <button className="primary-button" type="button" onClick={openCreate}>
          <FiPlus aria-hidden="true" /> New Follow-Up
        </button>
      </header>

      <section className="follow-up-summary" aria-label="Follow-up summary">
        <article className="summary-card overdue">
          <FiAlertTriangle />
          <strong>{overdueCount}</strong>
          <span>Overdue outreach</span>
        </article>
        <article className="summary-card today">
          <FiCalendar />
          <strong>{dueTodayCount}</strong>
          <span>Due today</span>
        </article>
        <article className="summary-card upcoming">
          <FiCheck />
          <strong>{upcomingCount}</strong>
          <span>Upcoming</span>
        </article>
      </section>

      {error && (
        <p className="feedback error" role="alert">
          {error}
        </p>
      )}

      <section className="follow-up-records">
        <div className="records-heading">
          <div>
            <h2>
              Client follow-up records <span>{followUps.length} active</span>
            </h2>
            <div className="filter-tabs">
              {['All', 'Overdue', 'Due Today', 'Upcoming'].map((option) => (
                <button
                  className={filter === option ? 'selected' : ''}
                  key={option}
                  type="button"
                  onClick={() => setFilter(option)}
                >
                  {option}
                </button>
              ))}
            </div>
          </div>
          <label className="search-field">
            <FiSearch aria-hidden="true" />
            <input
              aria-label="Filter follow-ups"
              placeholder="Filter client, reason, or stage..."
              value={search}
              onChange={(event) => setSearch(event.target.value)}
            />
          </label>
        </div>

        {loading ? (
          <p role="status">Loading follow-ups...</p>
        ) : visibleFollowUps.length === 0 ? (
          <p className="empty-state">No follow-ups match your filters.</p>
        ) : (
          <div className="follow-up-table-wrap">
            <table className="follow-up-table">
              <thead>
                <tr>
                  <th>Client</th>
                  <th>Follow-up reason</th>
                  <th>Related stage</th>
                  <th>Due date</th>
                  <th>Priority</th>
                  <th>Status</th>
                  <th>
                    <span className="sr-only">Actions</span>
                  </th>
                </tr>
              </thead>
              <tbody>
                {visibleFollowUps.map((followUp) => {
                  const client = clientById.get(followUp.client_id)
                  return (
                    <tr key={followUp.id}>
                      <td>
                        <strong>{client?.name || `Client #${followUp.client_id}`}</strong>
                        <small>{client?.email || 'Advisor client'}</small>
                      </td>
                      <td>{followUp.reason}</td>
                      <td>
                        <span className="stage-pill">
                          {stageShortName(followUp.financial_planning_stage)}
                        </span>
                      </td>
                      <td>{formatDate(followUp.due_date)}</td>
                      <td>
                        <span className={`priority-pill ${followUp.priority.toLowerCase()}`}>
                          {followUp.priority}
                        </span>
                      </td>
                      <td>
                        <select
                          className={`status-select ${followUp.status.toLowerCase().replace(' ', '-')}`}
                          aria-label={`Status for ${client?.name || followUp.client_id}`}
                          value={followUp.status}
                          onChange={(event) =>
                            void handleStatusChange(followUp, event.target.value)
                          }
                        >
                          {statuses.map((status) => (
                            <option key={status}>{status}</option>
                          ))}
                        </select>
                      </td>
                      <td>
                        <button
                          className="text-button"
                          type="button"
                          onClick={() => openEdit(followUp)}
                        >
                          Edit
                        </button>
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        )}
      </section>

      {isModalOpen && (
        <div className="modal-backdrop" role="presentation">
          <form className="follow-up-modal" onSubmit={(event) => void handleSubmit(event)}>
            <div className="modal-heading">
              <div>
                <p className="eyebrow">{editing ? 'Update record' : 'New record'}</p>
                <h2>{editing ? 'Edit follow-up' : 'New Follow-Up'}</h2>
              </div>
              <button
                type="button"
                className="modal-close"
                onClick={() => setIsModalOpen(false)}
                aria-label="Close"
              >
                ×
              </button>
            </div>
            {!editing && (
              <label>
                Client
                <select
                  required
                  value={form.client_id}
                  onChange={(event) => setForm({ ...form, client_id: event.target.value })}
                >
                  <option value="">Select a client</option>
                  {clients.map((client) => (
                    <option key={client.id} value={client.id}>
                      {client.name}
                    </option>
                  ))}
                </select>
              </label>
            )}
            <label>
              Reason
              <textarea
                required
                maxLength={2000}
                value={form.reason}
                onChange={(event) => setForm({ ...form, reason: event.target.value })}
              />
            </label>
            <div className="form-grid">
              <label>
                Planning stage
                <select
                  required
                  value={form.financial_planning_stage}
                  onChange={(event) =>
                    setForm({ ...form, financial_planning_stage: event.target.value })
                  }
                >
                  <option value="">Select stage</option>
                  {stages.map((stage) => (
                    <option key={stage}>{stage}</option>
                  ))}
                </select>
              </label>
              <label>
                Due date
                <input
                  required
                  type="date"
                  value={form.due_date}
                  onChange={(event) => setForm({ ...form, due_date: event.target.value })}
                />
              </label>
              <label>
                Priority
                <select
                  value={form.priority}
                  onChange={(event) => setForm({ ...form, priority: event.target.value })}
                >
                  {priorities.map((priority) => (
                    <option key={priority}>{priority}</option>
                  ))}
                </select>
              </label>
              <label>
                Status
                <select
                  value={form.status}
                  onChange={(event) => setForm({ ...form, status: event.target.value })}
                >
                  {statuses.map((status) => (
                    <option key={status}>{status}</option>
                  ))}
                </select>
              </label>
            </div>
            {formError && (
              <p className="feedback error" role="alert">
                {formError}
              </p>
            )}
            <div className="modal-actions">
              <button
                type="button"
                className="secondary-button"
                onClick={() => setIsModalOpen(false)}
              >
                Cancel
              </button>
              <button type="submit" className="primary-button" disabled={saving}>
                {saving ? 'Saving...' : editing ? 'Save changes' : 'Create follow-up'}
              </button>
            </div>
          </form>
        </div>
      )}
    </main>
  )
}

export default FollowUps
