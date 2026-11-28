
import { useEffect, useState } from 'react'
import { FiCreditCard, FiUser } from 'react-icons/fi'
import { getClientGoals, createClientGoals, deleteClientGoal, } from '../../services/GoalsApi'
import GoalsCard from './GoalsCard'
import GoalsForm from './GoalsForm'
import '../../styles/Clients.css'

function ClientOverview({ client }) {
  const [goals, setGoals] = useState([])
  const [goalsLoading, setGoalsLoading] = useState(true)
  const [goalsError, setGoalsError] = useState('')
  const [isGoalsFormOpen, setIsGoalsFormOpen] = useState(false)

  const clientId = client.id

  useEffect(() => {
    let active = true

    async function loadGoals() {
      setGoalsLoading(true)
      setGoalsError('')
      setGoals([])

      try {
        const data = await getClientGoals(clientId)

        if (active) {
          setGoals(data)
        }
      } catch (error) {
        if (active) {
          setGoalsError(error.message)
        }
      } finally {
        if (active) {
          setGoalsLoading(false)
        }
      }
    }

    loadGoals()

    return () => {
      active = false
    }
  }, [clientId])

   // Save selected financial goals
  const handleSaveGoals = async (selectedGoals) => {
    await createClientGoals(clientId, selectedGoals)

    // Reload goals from the database
    const updatedGoals = await getClientGoals(clientId)

    setGoals(updatedGoals)
    setIsGoalsFormOpen(false)
  }
  
  const handleDeleteGoal = async (goalId) => {
  await deleteClientGoal(clientId, goalId)

  const updatedGoals = await getClientGoals(clientId)
  setGoals(updatedGoals)
}

  const details = [
    ['Email', client.email],
    ['Phone number', client.phone_number],
    ['Address', client.address],
    ['Age', client.age == null ? null : `${client.age} years`],
    ['Occupation', client.occupation],
    ['Planning stage', client.timeline],
  ]

  return (
    <div className="client-overview">
      <section className="client-summary-card">
        <div className="overview-section-header">
          <FiUser />
          <h3>Client Profile Summary</h3>
        </div>

        <dl className="client-summary-grid">
          {details.map(([label, value]) => (
            <div className="client-summary-item" key={label}>
              <dt>{label}</dt>
              <dd>{value || 'Not provided'}</dd>
            </div>
          ))}
        </dl>
      </section>

      <div className="client-overview-grid">
        {/* Financial Snapshot will be implemented separately. */}
        <section className="financial-snapshot-card">
          <div className="overview-section-header">
            <FiCreditCard />
            <h3>Financial Snapshot</h3>
          </div>
        </section>

        <GoalsCard
          goals={goals}
          loading={goalsLoading}
          error={goalsError}
          onAddDetails={() => setIsGoalsFormOpen(true)}
          onDelete={handleDeleteGoal}
        />
      </div>
      {isGoalsFormOpen && (
        <GoalsForm
           goals={goals}
           onClose={() => setIsGoalsFormOpen(false)}
           onSave={handleSaveGoals}
        />
      )}
    </div>
  )
}
export default ClientOverview

