
import { useEffect, useState } from 'react'
import { FiPlus, FiX } from 'react-icons/fi'
import { getGoalTypes } from '../../services/GoalsApi'
import '../../styles/GoalsForm.css'

const HORIZONS = [
  {
    duration: 'Short-term',
    title: 'Short-term goals',
    years: '1–3 years',
  },
  {
    duration: 'Medium-term',
    title: 'Mid-range goals',
    years: '3–7 years',
  },
  {
    duration: 'Long-term',
    title: 'Long-term goals',
    years: '7+ years',
  },
]

function getGoalKey(goal) {
  return `${goal.duration}:${goal.type}`
}

function GoalsForm({
  goals = [],
  onClose,
  onSave,
}) {
  const [goalTypes, setGoalTypes] = useState([])
  const [selectedGoals, setSelectedGoals] = useState([])
  const [customGoals, setCustomGoals] = useState([])
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    let active = true

    async function loadGoalTypes() {
      try {
        const data = await getGoalTypes()

        if (!active) return

        setGoalTypes(data)

        // Restore previously selected predefined goals.
        setSelectedGoals(
          goals
            .filter((goal) => goal.type !== 'other')
            .map(getGoalKey),
        )

        // Restore previously saved custom goals.
        setCustomGoals(
          goals
            .filter((goal) => goal.type === 'other')
            .map((goal, index) => ({
              id: `existing-${goal.id ?? index}`,
              name: goal.name,
              duration: goal.duration,
            })),
        )
      } catch (err) {
        if (active) {
          setError(err.message || 'Unable to load financial goals.')
        }
      } finally {
        if (active) {
          setLoading(false)
        }
      }
    }

    loadGoalTypes()

    return () => {
      active = false
    }
  }, [goals])

  const toggleGoal = (goal) => {
    const key = getGoalKey(goal)

    setSelectedGoals((previous) =>
      previous.includes(key)
        ? previous.filter((item) => item !== key)
        : [...previous, key],
    )
  }

  const addCustomGoal = () => {
    setCustomGoals((previous) => [
      ...previous,
      {
        id: `new-${previous.length}-${Date.now()}`,
        name: '',
        duration: '',
      },
    ])
  }

  const updateCustomGoal = (id, field, value) => {
    setCustomGoals((previous) =>
      previous.map((goal) =>
        goal.id === id
          ? { ...goal, [field]: value }
          : goal,
      ),
    )
  }

  const removeCustomGoal = (id) => {
    setCustomGoals((previous) =>
      previous.filter((goal) => goal.id !== id),
    )
  }

  const handleSubmit = async (event) => {
    event.preventDefault()
    setError('')

    const incompleteCustomGoal = customGoals.some(
      (goal) => !goal.name.trim() || !goal.duration,
    )

    if (incompleteCustomGoal) {
      setError(
        'Please enter a description and timeframe for every custom goal.',
      )
      return
    }

    const selectedPredefinedGoals = goalTypes
    .filter((goal) =>
        selectedGoals.includes(`${goal.duration}:${goal.code}`),
    )
    .map((goal) => ({
        duration: goal.duration,
        type: goal.code,
    }))

    const selectedCustomGoals = customGoals.map((goal) => ({
      duration: goal.duration,
      type: 'other',
      name: goal.name.trim(),
    }))

    const payload = [
      ...selectedPredefinedGoals,
      ...selectedCustomGoals,
    ]
    console.log('Selected goals:', selectedGoals)
    console.log('Custom goals:', customGoals)
    console.log('Final payload:', payload)

    try {
      setSaving(true)
      await onSave(payload)
    } catch (err) {
      setError(err.message || 'Unable to save financial goals.')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="goals-modal-overlay">
      <section
        className="goals-modal"
        role="dialog"
        aria-modal="true"
        aria-labelledby="goals-form-title"
      >
        <div className="goals-modal-header">
          <div>
            <h2 id="goals-form-title">Add Financial Goals</h2>
            <p>
              Select any goals that apply to your client.
              This section is optional.
            </p>
          </div>

          <button
            type="button"
            className="goals-close-button"
            onClick={onClose}
            aria-label="Close form"
            disabled={saving}
          >
            <FiX />
          </button>
        </div>

        {loading ? (
          <p role="status" className="goals-form-loading">
            Loading financial goal options...
          </p>
        ) : (
          <form onSubmit={handleSubmit}>
            <div className="goals-modal-body">
              {HORIZONS.map((horizon) => {
                const options = goalTypes.filter(
                  (goal) => goal.duration === horizon.duration,
                )

                return (
                  <section
                    className="goals-form-horizon"
                    key={horizon.duration}
                  >
                    <div className="goals-form-horizon-header">
                      <h3>{horizon.title}</h3>
                      <span>{horizon.years}</span>
                    </div>

                    {options.length === 0 ? (
                      <p>No predefined goals available.</p>
                    ) : (
                      <div className="goals-options-list">
                        {options.map((goal) => (
                          <label
                            className="goals-option"
                            key={goal.code}
                          >
                            <input
                              type="checkbox"
                              checked={selectedGoals.includes(
                                getGoalKey({
                                  duration: goal.duration,
                                  type: goal.code,
                                }),
                              )}
                              onChange={() => toggleGoal({
                                duration: goal.duration,
                                type: goal.code,
                              })}
                            />
                            <span>{goal.name}</span>
                          </label>
                        ))}
                      </div>
                    )}
                  </section>
                )
              })}

              <section className="custom-goals-section">
                <div className="goals-form-horizon-header">
                  <h3>Custom goals</h3>
                  <span>Optional</span>
                </div>

                <p>
                  Add a goal that isn't included in the predefined list.
                </p>

                {customGoals.map((goal) => (
                  <div className="custom-goal-fields" key={goal.id}>
                    <label>
                      Goal description
                      <input
                        type="text"
                        value={goal.name}
                        onChange={(event) =>
                          updateCustomGoal(
                            goal.id,
                            'name',
                            event.target.value,
                          )
                        }
                        placeholder="e.g. Start my own business"
                        maxLength={255}
                      />
                    </label>

                    <label>
                      Timeframe
                      <select
                        value={goal.duration}
                        onChange={(event) =>
                          updateCustomGoal(
                            goal.id,
                            'duration',
                            event.target.value,
                          )
                        }
                      >
                        <option value="">Select timeframe</option>
                        {HORIZONS.map((horizon) => (
                          <option
                            key={horizon.duration}
                            value={horizon.duration}
                          >
                            {horizon.title} ({horizon.years})
                          </option>
                        ))}
                      </select>
                    </label>

                    <button
                      type="button"
                      className="remove-custom-goal"
                      onClick={() => removeCustomGoal(goal.id)}
                      aria-label="Remove custom goal"
                    >
                      <FiX />
                      Remove
                    </button>
                  </div>
                ))}

                <button
                  type="button"
                  className="add-custom-goal-button"
                  onClick={addCustomGoal}
                >
                  <FiPlus />
                  Add custom goal
                </button>
              </section>

              {error && (
                <p className="goals-form-error" role="alert">
                  {error}
                </p>
              )}
            </div>

            <div className="goals-modal-actions">
              <button
                type="button"
                className="goals-cancel-button"
                onClick={onClose}
                disabled={saving}
              >
                Cancel
              </button>

              <button
                type="submit"
                className="goals-save-button"
                disabled={saving || loading}
              >
                {saving ? 'Saving...' : 'Save goals'}
              </button>
            </div>
          </form>
        )}
      </section>
    </div>
  )
}

export default GoalsForm
