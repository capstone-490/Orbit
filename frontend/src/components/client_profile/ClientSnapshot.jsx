
import { useEffect, useState } from 'react'
import { API_BASE_URL, withAuthCredentials } from '../../services/AuthApi'

const emptyExpense = () => ({
  description: '',
  amount: '',
  frequency: 'monthly',
})

const emptyIncome = () => ({
  description: '',
  amount: '',
  frequency: 'annually',
})

const emptyAsset = () => ({
  description: '',
  value: '',
})

const emptyDebt = () => ({
  description: '',
  balance: '',
  interest_rate: '',
})

const formatAmount = (value) =>
  Number(value).toLocaleString(undefined, {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })

function ClientSnapshot({ client }) {
  const [expenses, setExpenses] = useState([])
  const [income, setIncome] = useState([])
  const [assets, setAssets] = useState([])
  const [debts, setDebts] = useState([])
  const [totals, setTotals] = useState({
    expenses: { weekly_total: 0, monthly_total: 0, annual_total: 0 },
    income: { weekly_total: 0, monthly_total: 0, annual_total: 0 },
    revenue: { weekly_total: 0, monthly_total: 0, annual_total: 0 },
    assets: { total: 0 },
    debts: { total: 0 },
    net_worth: 0,
  })
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')

  useEffect(() => {
    let active = true

    const fetchSnapshot = async () => {
      try {
        const response = await fetch(
          `${API_BASE_URL}/clients/${client.id}/financial-snapshot`,
          withAuthCredentials(),
        )
        if (!response.ok) throw new Error('Unable to load the financial snapshot.')
        const snapshot = await response.json()
        if (!active) return
        setExpenses(
          snapshot.expenses.map(({ id, description, amount, frequency }) => ({
            id,
            description,
            amount: String(amount),
            frequency,
          })),
        )
        setIncome(
          snapshot.income.map(({ id, description, amount, frequency }) => ({
            id,
            description,
            amount: String(amount),
            frequency,
          })),
        )
        setAssets(
          snapshot.assets.map(({ id, description, value }) => ({
            id,
            description,
            value: String(value),
          })),
        )
        setDebts(
          snapshot.debts.map(({ id, description, balance, interest_rate }) => ({
            id,
            description,
            balance: String(balance),
            interest_rate: String(interest_rate),
          })),
        )
        setTotals({
          expenses: snapshot.totals.expenses,
          income: snapshot.totals.income,
          revenue: snapshot.totals.revenue,
          assets: snapshot.totals.assets,
          debts: snapshot.totals.debts,
          net_worth: snapshot.totals.net_worth,
        })
      } catch (fetchError) {
        if (active) setError(fetchError.message)
      } finally {
        if (active) setLoading(false)
      }
    }

    void fetchSnapshot()
    return () => {
      active = false
    }
  }, [client.id])

  const updateExpense = (id, field, value) => {
    setExpenses((current) =>
      current.map((expense) => (expense.id === id ? { ...expense, [field]: value } : expense)),
    )
  }

  const updateIncome = (id, field, value) => {
    setIncome((current) =>
      current.map((inc) => (inc.id === id ? { ...inc, [field]: value } : inc)),
    )
  }

  const updateAsset = (id, field, value) => {
    setAssets((current) =>
      current.map((asset) => (asset.id === id ? { ...asset, [field]: value } : asset)),
    )
  }

  const updateDebt = (id, field, value) => {
    setDebts((current) =>
      current.map((debt) => (debt.id === id ? { ...debt, [field]: value } : debt)),
    )
  }

  const handleSave = async (event) => {
    event.preventDefault()
    setError('')
    setSuccess('')

    // Validate expenses
    if (
      expenses.some(
        (expense) =>
          !expense.description.trim() ||
          !Number.isFinite(Number(expense.amount)) ||
          Number(expense.amount) <= 0,
      )
    ) {
      setError('Each expense needs a description and an amount greater than zero.')
      return
    }

    // Validate income
    if (
      income.some(
        (inc) =>
          !inc.description.trim() ||
          !Number.isFinite(Number(inc.amount)) ||
          Number(inc.amount) <= 0,
      )
    ) {
      setError('Each income item needs a description and an amount greater than zero.')
      return
    }

    // Validate assets
    if (
      assets.some(
        (asset) =>
          !asset.description.trim() ||
          !Number.isFinite(Number(asset.value)) ||
          Number(asset.value) <= 0,
      )
    ) {
      setError('Each asset needs a description and a value greater than zero.')
      return
    }

    // Validate debts
    if (
      debts.some(
        (debt) =>
          !debt.description.trim() ||
          !Number.isFinite(Number(debt.balance)) ||
          Number(debt.balance) <= 0 ||
          !Number.isFinite(Number(debt.interest_rate)) ||
          Number(debt.interest_rate) < 0,
      )
    ) {
      setError(
        'Each debt needs a description, balance greater than zero, and a non-negative interest rate.',
      )
      return
    }

    setSaving(true)
    try {
      const response = await fetch(
        `${API_BASE_URL}/clients/${client.id}/financial-snapshot`,
        withAuthCredentials({
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            expenses: expenses.map(({ description, amount, frequency }) => ({
              description: description.trim(),
              amount: Number(amount),
              frequency,
            })),
            income: income.map(({ description, amount, frequency }) => ({
              description: description.trim(),
              amount: Number(amount),
              frequency,
            })),
            assets: assets.map(({ description, value }) => ({
              description: description.trim(),
              value: Number(value),
            })),
            debts: debts.map(({ description, balance, interest_rate }) => ({
              description: description.trim(),
              balance: Number(balance),
              interest_rate: Number(interest_rate),
            })),
          }),
        }),
      )
      if (!response.ok) {
        const details = await response.json().catch(() => ({}))
        throw new Error(
          typeof details.detail === 'string'
            ? details.detail
            : 'Unable to save the financial snapshot.',
        )
      }

      const snapshot = await response.json()
      setExpenses(
        snapshot.expenses.map(({ id, description, amount, frequency }) => ({
          id,
          description,
          amount: String(amount),
          frequency,
        })),
      )
      setIncome(
        snapshot.income.map(({ id, description, amount, frequency }) => ({
          id,
          description,
          amount: String(amount),
          frequency,
        })),
      )
      setAssets(
        snapshot.assets.map(({ id, description, value }) => ({
          id,
          description,
          value: String(value),
        })),
      )
      setDebts(
        snapshot.debts.map(({ id, description, balance, interest_rate }) => ({
          id,
          description,
          balance: String(balance),
          interest_rate: String(interest_rate),
        })),
      )
      setTotals({
        expenses: snapshot.totals.expenses,
        income: snapshot.totals.income,
        revenue: snapshot.totals.revenue,
        assets: snapshot.totals.assets,
        debts: snapshot.totals.debts,
        net_worth: snapshot.totals.net_worth,
      })
      setSuccess('Financial snapshot saved.')
    } catch (saveError) {
      setError(saveError.message)
    } finally {
      setSaving(false)
    }
  }

  if (loading) return <p role="status">Loading financial snapshot...</p>

  return (
    <section className="client-snapshot" aria-labelledby="client-snapshot-title">
      <div className="client-snapshot-heading">
        <div>
          <h2 id="client-snapshot-title">Financial snapshot</h2>
          <p>Add optional income, expense, asset and debt items from the client's financial statements.</p>
        </div>
      </div>

      {error && <p className="clients-error" role="alert">{error}</p>}
      {success && <p className="client-profile-success" role="status">{success}</p>}

      <form onSubmit={handleSave}>
        {/* Income Section */}
        <fieldset className="client-snapshot-section">
          <legend>Income</legend>
          <div className="client-snapshot-totals">
            <div>
              <span>Weekly</span>
              <strong>{formatAmount(totals.income.weekly_total)}</strong>
            </div>
            <div>
              <span>Monthly</span>
              <strong>{formatAmount(totals.income.monthly_total)}</strong>
            </div>
            <div>
              <span>Annual</span>
              <strong>{formatAmount(totals.income.annual_total)}</strong>
            </div>
          </div>
          <button
            type="button"
            className="client-save-button"
            onClick={() => setIncome((current) => [...current, emptyIncome()])}
          >
            Add income
          </button>
          {income.length === 0 ? (
            <p className="client-snapshot-empty">No income added yet.</p>
          ) : (
            <div className="client-snapshot-list">
              {income.map((inc) => (
                <div className="client-snapshot-expense" key={inc.id}>
                  <label>
                    Income
                    <input
                      type="text"
                      aria-label="Income description"
                      maxLength="120"
                      value={inc.description}
                      onChange={(event) =>
                        updateIncome(inc.id, 'description', event.target.value)
                      }
                    />
                  </label>
                  <label>
                    Amount
                    <input
                      type="number"
                      aria-label="Income amount"
                      min="0.01"
                      step="0.01"
                      value={inc.amount}
                      onChange={(event) => updateIncome(inc.id, 'amount', event.target.value)}
                    />
                  </label>
                  <label>
                    Frequency
                    <select
                      aria-label="Income frequency"
                      value={inc.frequency}
                      onChange={(event) =>
                        updateIncome(inc.id, 'frequency', event.target.value)
                      }
                    >
                      <option value="weekly">Weekly</option>
                      <option value="monthly">Monthly</option>
                      <option value="annually">Annually</option>
                    </select>
                  </label>
                  <button
                    type="button"
                    className="client-snapshot-remove"
                    aria-label={`Remove ${inc.description || 'income'}`}
                    onClick={() => setIncome((current) => current.filter((item) => item.id !== inc.id))}
                  >
                    Remove
                  </button>
                </div>
              ))}
            </div>
          )}
        </fieldset>

        {/* Expenses Section */}
        <fieldset className="client-snapshot-section">
          <legend>Expenses</legend>
          <div className="client-snapshot-totals">
            <div>
              <span>Weekly</span>
              <strong>{formatAmount(totals.expenses.weekly_total)}</strong>
            </div>
            <div>
              <span>Monthly</span>
              <strong>{formatAmount(totals.expenses.monthly_total)}</strong>
            </div>
            <div>
              <span>Annual</span>
              <strong>{formatAmount(totals.expenses.annual_total)}</strong>
            </div>
          </div>
          <button
            type="button"
            className="client-save-button"
            onClick={() => setExpenses((current) => [...current, emptyExpense()])}
          >
            Add expense
          </button>
          {expenses.length === 0 ? (
            <p className="client-snapshot-empty">No expenses added yet.</p>
          ) : (
            <div className="client-snapshot-list">
              {expenses.map((expense) => (
                <div className="client-snapshot-expense" key={expense.id}>
                  <label>
                    Expense
                    <input
                      type="text"
                      aria-label="Expense description"
                      maxLength="120"
                      value={expense.description}
                      onChange={(event) =>
                        updateExpense(expense.id, 'description', event.target.value)
                      }
                    />
                  </label>
                  <label>
                    Amount
                    <input
                      type="number"
                      aria-label="Expense amount"
                      min="0.01"
                      step="0.01"
                      value={expense.amount}
                      onChange={(event) =>
                        updateExpense(expense.id, 'amount', event.target.value)
                      }
                    />
                  </label>
                  <label>
                    Frequency
                    <select
                      aria-label="Expense frequency"
                      value={expense.frequency}
                      onChange={(event) =>
                        updateExpense(expense.id, 'frequency', event.target.value)
                      }
                    >
                      <option value="weekly">Weekly</option>
                      <option value="monthly">Monthly</option>
                      <option value="annually">Annually</option>
                    </select>
                  </label>
                  <button
                    type="button"
                    className="client-snapshot-remove"
                    aria-label={`Remove ${expense.description || 'expense'}`}
                    onClick={() =>
                      setExpenses((current) => current.filter((item) => item.id !== expense.id))
                    }
                  >
                    Remove
                  </button>
                </div>
              ))}
            </div>
          )}
        </fieldset>

        {/* Revenue Section */}
        <fieldset className="client-snapshot-section">
          <legend>Revenue</legend>
          <p className="client-snapshot-info">Income minus expenses</p>
          <div className="client-snapshot-totals">
            <div>
              <span>Weekly</span>
              <strong>{formatAmount(totals.revenue.weekly_total)}</strong>
            </div>
            <div>
              <span>Monthly</span>
              <strong>{formatAmount(totals.revenue.monthly_total)}</strong>
            </div>
            <div>
              <span>Annual</span>
              <strong>{formatAmount(totals.revenue.annual_total)}</strong>
            </div>
          </div>
        </fieldset>

        {/* Assets Section */}
        <fieldset className="client-snapshot-section">
          <legend>Assets</legend>
          <div className="client-snapshot-totals">
            <div>
              <span>Total</span>
              <strong>{formatAmount(totals.assets.total)}</strong>
            </div>
          </div>
          <button
            type="button"
            className="client-save-button"
            onClick={() => setAssets((current) => [...current, emptyAsset()])}
          >
            Add asset
          </button>
          {assets.length === 0 ? (
            <p className="client-snapshot-empty">No assets added yet.</p>
          ) : (
            <div className="client-snapshot-list">
              {assets.map((asset) => (
                <div className="client-snapshot-expense" key={asset.id}>
                  <label>
                    Asset
                    <input
                      type="text"
                      aria-label="Asset description"
                      maxLength="120"
                      value={asset.description}
                      onChange={(event) =>
                        updateAsset(asset.id, 'description', event.target.value)
                      }
                    />
                  </label>
                  <label>
                    Value
                    <input
                      type="number"
                      aria-label="Asset value"
                      min="0.01"
                      step="0.01"
                      value={asset.value}
                      onChange={(event) => updateAsset(asset.id, 'value', event.target.value)}
                    />
                  </label>
                  <button
                    type="button"
                    className="client-snapshot-remove"
                    aria-label={`Remove ${asset.description || 'asset'}`}
                    onClick={() =>
                      setAssets((current) => current.filter((item) => item.id !== asset.id))
                    }
                  >
                    Remove
                  </button>
                </div>
              ))}
            </div>
          )}
        </fieldset>

        {/* Debts Section */}
        <fieldset className="client-snapshot-section">
          <legend>Debts</legend>
          <div className="client-snapshot-totals">
            <div>
              <span>Total</span>
              <strong>{formatAmount(totals.debts.total)}</strong>
            </div>
          </div>
          <button
            type="button"
            className="client-save-button"
            onClick={() => setDebts((current) => [...current, emptyDebt()])}
          >
            Add debt
          </button>
          {debts.length === 0 ? (
            <p className="client-snapshot-empty">No debts added yet.</p>
          ) : (
            <div className="client-snapshot-list">
              {debts.map((debt) => (
                <div className="client-snapshot-expense" key={debt.id}>
                  <label>
                    Debt
                    <input
                      type="text"
                      aria-label="Debt description"
                      maxLength="120"
                      value={debt.description}
                      onChange={(event) =>
                        updateDebt(debt.id, 'description', event.target.value)
                      }
                    />
                  </label>
                  <label>
                    Balance
                    <input
                      type="number"
                      aria-label="Debt balance"
                      min="0.01"
                      step="0.01"
                      value={debt.balance}
                      onChange={(event) => updateDebt(debt.id, 'balance', event.target.value)}
                    />
                  </label>
                  <label>
                    Interest Rate (%)
                    <input
                      type="number"
                      aria-label="Interest rate"
                      min="0"
                      step="0.01"
                      value={debt.interest_rate}
                      onChange={(event) =>
                        updateDebt(debt.id, 'interest_rate', event.target.value)
                      }
                    />
                  </label>
                  <button
                    type="button"
                    className="client-snapshot-remove"
                    aria-label={`Remove ${debt.description || 'debt'}`}
                    onClick={() =>
                      setDebts((current) => current.filter((item) => item.id !== debt.id))
                    }
                  >
                    Remove
                  </button>
                </div>
              ))}
            </div>
          )}
        </fieldset>

        {/* Net Worth Summary */}
        <fieldset className="client-snapshot-net-worth">
          <legend className="client-snapshot-visually-hidden">Net worth calculation</legend>
          <div>
            <span>Total Assets</span>
            <strong>{formatAmount(totals.assets.total)}</strong>
          </div>
          <div>
            <span>Total Debts</span>
            <strong>{formatAmount(totals.debts.total)}</strong>
          </div>
          <div className="net-worth-line">
            <span>Net Worth</span>
            <strong>{formatAmount(totals.net_worth)}</strong>
          </div>
        </fieldset>

        <div className="client-modal-actions">
          <button type="submit" className="client-save-button" disabled={saving}>
            {saving ? 'Saving...' : 'Save snapshot'}
          </button>
        </div>
      </form>
    </section>
  )
}

export default ClientSnapshot