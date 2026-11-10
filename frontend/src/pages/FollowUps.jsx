//Below 50% AI generated
import { useEffect, useMemo, useState } from 'react'
import {
  FiAlertTriangle,
  FiCalendar,
  FiCheck,
  FiCopy,
  FiEdit2,
  FiMail,
  FiPhone,
  FiPlus,
  FiSearch,
  FiUsers,
} from 'react-icons/fi'
import { withAuthCredentials } from '../services/AuthApi'
import {
  createFollowUp,
  getFollowUps,
  updateFollowUp,
  updateFollowUpStatus,
} from '../services/FollowUpsApi'
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

function isTerminalStatus(status) {
  return status === 'Completed' || status === 'Cancelled'
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
  const [emailDraft, setEmailDraft] = useState(null)
  const [contactNotice, setContactNotice] = useState('')

  const clientById = useMemo(() => new Map(clients.map((client) => [client.id, client])), [clients])
  const selectedClient = editing
    ? clientById.get(editing.client_id)
    : clientById.get(Number(form.client_id))

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
        (filter === 'Overdue' && !isTerminalStatus(followUp.status) && followUp.due_date < today) ||
        (filter === 'Due Today' && followUp.due_date === today) ||
        (filter === 'Upcoming' && !isTerminalStatus(followUp.status) && followUp.due_date > today)
      return matchesSearch && matchesFilter
    })
  }, [clientById, filter, followUps, search])

  const today = getLocalDateKey()
  const overdueCount = followUps.filter(
    (item) => !isTerminalStatus(item.status) && item.due_date < today,
  ).length
  const dueTodayCount = followUps.filter((item) => item.due_date === today).length
  const upcomingCount = followUps.filter(
    (item) => !isTerminalStatus(item.status) && item.due_date > today,
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

  function openEmailComposer(followUp, client) {
    if (!client?.email) {
      setError('This client does not have an email address on file.')
      return
    }

    setEmailDraft({
      client,
      followUp,
      contactMethod: 'email',
      subject: `Follow-up: ${followUp.reason}`,
      body: `Hello ${client.name},\n\nI am following up regarding ${followUp.reason.toLowerCase()}.\n\nBest regards`,
      discussionNotes: followUp.discussion_notes || '',
    })
    setContactNotice('')
  }

  async function copyContactValue(value, label) {
    try {
      await navigator.clipboard.writeText(value)
      setContactNotice(`${label} copied to clipboard.`)
    } catch {
      setContactNotice(`Unable to copy the ${label.toLowerCase()}.`)
    }
  }

  async function saveDiscussionNotes() {
    if (!emailDraft) return
    try {
      await updateFollowUp(emailDraft.followUp.id, {
        discussion_notes: emailDraft.discussionNotes.trim(),
      })
      setFollowUps((current) =>
        current.map((item) =>
          item.id === emailDraft.followUp.id
            ? { ...item, discussion_notes: emailDraft.discussionNotes.trim() }
            : item,
        ),
      )
      setEmailDraft({
        ...emailDraft,
        followUp: {
          ...emailDraft.followUp,
          discussion_notes: emailDraft.discussionNotes.trim(),
        },
        discussionNotes: emailDraft.discussionNotes.trim(),
      })
      setContactNotice('Discussion notes saved.')
      window.setTimeout(() => {
        setEmailDraft(null)
      }, 1000)
    } catch (notesError) {
      setContactNotice(notesError.message)
    }
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

  async function handlePriorityChange(followUp, priority) {
    try {
      await updateFollowUp(followUp.id, { priority })
      setFollowUps((current) =>
        current.map((item) => (item.id === followUp.id ? { ...item, priority } : item)),
      )
    } catch (priorityError) {
      setError(priorityError.message)
    }
  }

  async function handleFollowUpFieldChange(followUp, field, value) {
    try {
      await updateFollowUp(followUp.id, { [field]: value })
      setFollowUps((current) =>
        current.map((item) => (item.id === followUp.id ? { ...item, [field]: value } : item)),
      )
    } catch (fieldError) {
      setError(fieldError.message)
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
                  <th>Contact</th>
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
                        <small>{client?.email || 'No email on file'}</small>
                      </td>
                      <td>{followUp.reason}</td>
                      <td>
                        <select
                          className="inline-field-select stage-select"
                          aria-label={`Planning stage for ${client?.name || followUp.client_id}`}
                          value={followUp.financial_planning_stage}
                          onChange={(event) =>
                            void handleFollowUpFieldChange(
                              followUp,
                              'financial_planning_stage',
                              event.target.value,
                            )
                          }
                        >
                          {stages.map((stage) => (
                            <option key={stage} value={stage}>
                              {stageShortName(stage)}
                            </option>
                          ))}
                        </select>
                      </td>
                      <td>
                        <input
                          className="inline-date-input"
                          aria-label={`Due date for ${client?.name || followUp.client_id}`}
                          type="date"
                          value={followUp.due_date}
                          onChange={(event) =>
                            void handleFollowUpFieldChange(followUp, 'due_date', event.target.value)
                          }
                        />
                      </td>
                      <td>
                        <select
                          className={`priority-pill ${followUp.priority.toLowerCase()}`}
                          aria-label={`Priority for ${client?.name || followUp.client_id}`}
                          value={followUp.priority}
                          onChange={(event) =>
                            void handlePriorityChange(followUp, event.target.value)
                          }
                        >
                          {priorities.map((priority) => (
                            <option key={priority}>{priority}</option>
                          ))}
                        </select>
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
                        {client?.email ? (
                          <button
                            className="email-button"
                            type="button"
                            onClick={() => openEmailComposer(followUp, client)}
                            aria-label={`Contact info for ${client.name}`}
                          >
                            <FiUsers aria-hidden="true" /> Contact info
                          </button>
                        ) : (
                          <span className="contact-missing">No email</span>
                        )}
                      </td>
                      <td>
                        <button
                          className="edit-button"
                          type="button"
                          onClick={() => openEdit(followUp)}
                        >
                          <FiEdit2 aria-hidden="true" /> Edit
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

            {selectedClient && (
              <section className="client-contact-card" aria-label="Client contact information">
                <div>
                  <strong>{selectedClient.name}</strong>
                  <small>Client contact information</small>
                </div>
                <div className="client-contact-links">
                  {selectedClient.email && (
                    <a href={`mailto:${selectedClient.email}`}>
                      <FiMail aria-hidden="true" /> {selectedClient.email}
                    </a>
                  )}
                  {selectedClient.phone_number && (
                    <a href={`tel:${selectedClient.phone_number}`}>
                      <FiPhone aria-hidden="true" /> {selectedClient.phone_number}
                    </a>
                  )}
                </div>
              </section>
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

      {emailDraft && (
        <div className="modal-backdrop email-composer-backdrop" role="presentation">
          <section
            className="email-composer"
            role="dialog"
            aria-modal="true"
            aria-labelledby="email-composer-title"
          >
            <div className="modal-heading">
              <div>
                <p className="eyebrow">Client engagement</p>
                <h2 id="email-composer-title">Send follow-up email</h2>
              </div>
              <button
                type="button"
                className="modal-close"
                onClick={() => setEmailDraft(null)}
                aria-label="Close email composer"
              >
                ×
              </button>
            </div>
            <div className="email-recipient">
              <span className="client-avatar">{emailDraft.client.name.charAt(0)}</span>
              <div>
                <strong>{emailDraft.client.name}</strong>
                <div className="contact-values">
                  <button
                    type="button"
                    className={`contact-method-button ${
                      emailDraft.contactMethod === 'email' ? 'selected' : ''
                    }`}
                    onClick={() => {
                      setEmailDraft({ ...emailDraft, contactMethod: 'email' })
                      setContactNotice('')
                    }}
                  >
                    <FiMail aria-hidden="true" /> Email
                  </button>
                  {emailDraft.client.phone_number ? (
                    <button
                      type="button"
                      className={`contact-method-button ${
                        emailDraft.contactMethod === 'phone' ? 'selected' : ''
                      }`}
                      onClick={() => {
                        setEmailDraft({ ...emailDraft, contactMethod: 'phone' })
                        setContactNotice('')
                      }}
                    >
                      <FiPhone aria-hidden="true" /> Phone
                    </button>
                  ) : (
                    <small>Phone not provided</small>
                  )}
                </div>
              </div>
            </div>
            <div className="selected-contact">
              <span>{emailDraft.contactMethod === 'email' ? 'Email address' : 'Phone number'}</span>
              <strong>
                {emailDraft.contactMethod === 'email'
                  ? emailDraft.client.email
                  : emailDraft.client.phone_number}
              </strong>
              <button
                type="button"
                className="copy-contact-button"
                onClick={() =>
                  void copyContactValue(
                    emailDraft.contactMethod === 'email'
                      ? emailDraft.client.email
                      : emailDraft.client.phone_number,
                    emailDraft.contactMethod === 'email' ? 'Email' : 'Phone number',
                  )
                }
              >
                <FiCopy aria-hidden="true" /> Copy
              </button>
            </div>
            {emailDraft.contactMethod === 'email' && (
              <label>
                Subject
                <input
                  value={emailDraft.subject}
                  onChange={(event) =>
                    setEmailDraft({ ...emailDraft, subject: event.target.value })
                  }
                />
              </label>
            )}
            <label>
              Discussion notes
              <textarea
                className="email-message"
                value={emailDraft.discussionNotes}
                placeholder="Record the outcome of your conversation with this client..."
                onChange={(event) =>
                  setEmailDraft({ ...emailDraft, discussionNotes: event.target.value })
                }
              />
            </label>
            <button
              type="button"
              className="save-notes-button"
              onClick={() => void saveDiscussionNotes()}
            >
              Save discussion
            </button>
            {contactNotice && <p className="contact-notice">{contactNotice}</p>}
            <div className="modal-actions">
              <button
                type="button"
                className="secondary-button"
                onClick={() => setEmailDraft(null)}
              >
                Cancel
              </button>
            </div>
          </section>
        </div>
      )}
    </main>
  )
}

export default FollowUps
