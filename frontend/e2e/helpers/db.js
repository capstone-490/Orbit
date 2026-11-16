// Substantial AI assistance used;

import { randomUUID } from 'node:crypto'
import pg from 'pg'

// Database connection

// Each Playwright worker maintains its own connection pool.
const databasePool = new pg.Pool({
  host: process.env.E2E_DB_HOST ?? '127.0.0.1',
  port: Number(process.env.E2E_DB_PORT ?? 55432),
  user: process.env.E2E_DB_USER ?? 'postgres',
  password: process.env.E2E_DB_PASSWORD ?? process.env.POSTGRES_PASSWORD ?? 'test_admin_password',
  database: process.env.E2E_DB_NAME ?? 'test_db',
  max: 4,
  allowExitOnIdle: true, // don't keep the worker alive after tests finish
})

// Execute a query and return its first result row.
async function executeQuery(query, values) {
  const result = await databasePool.query(query, values)
  return result.rows[0]
}

// Date helpers

// Keep one reference time per worker so test data uses a consistent date.
export const NOW = new Date()

const MILLISECONDS_PER_DAY = 24 * 60 * 60 * 1000

// Return a date relative to NOW. Negative values represent past dates.
export const daysFromNow = (days) => new Date(NOW.getTime() + days * MILLISECONDS_PER_DAY)

// Convert a relative date into YYYY-MM-DD using UTC.
export const dateOnlyFromNow = (days) => daysFromNow(days).toISOString().slice(0, 10)

// Test data utilities

// Generate a short identifier to keep test records unique.
const uid = () => randomUUID().slice(0, 8)

// Random North American phone number: area code and exchange start with 2-9 and aren't N11.
export function nanpPhone() {
  const part = () => {
    let n
    do {
      n = 200 + Math.floor(Math.random() * 800)
    } while (n % 100 === 11)
    return String(n)
  }
  const line = String(Math.floor(Math.random() * 10000)).padStart(4, '0')
  return `(${part()}) ${part()}-${line}`
}

// Clients

/**
 * Create a client associated with an advisor.
 * Optional overrides allow tests to customize individual database fields.
 */
export function createClient(advisorId, overrides = {}) {
  if (!advisorId) throw new Error('createClient: advisorId is required')

  const id = uid()
  const clientData = {
    name: `E2E Client ${id}`,
    email: `client-${id}@example.com`,
    phoneNumber: nanpPhone(),
    createdAt: NOW,
    ...overrides,
  }
  return executeQuery(
    `INSERT INTO clients (advisor_id, name, email, phone_number, created_at, updated_at)
     VALUES ($1, $2, $3, $4, $5, $5)
     RETURNING *`,
    [advisorId, clientData.name, clientData.email, clientData.phoneNumber, clientData.createdAt],
  )
}

// Retrieve a client using their email address.
export function findClientByEmail(email) {
  return executeQuery('SELECT * FROM clients WHERE lower(email) = lower($1)', [email])
}

export function findAdvisorByEmail(email) {
  return executeQuery('SELECT * FROM advisors WHERE lower(email) = lower($1)', [email])
}

// Meetings

// Reusable meeting configurations for different dashboard scenarios.
export const MEETING = {
  future: { start: daysFromNow(2), durationMinutes: 30, status: 'Scheduled' },
  overdue: { start: daysFromNow(-2), durationMinutes: 30, status: 'Scheduled' },
  completed: { start: daysFromNow(-3), durationMinutes: 45, status: 'Completed' },
  cancelled: { start: daysFromNow(3), durationMinutes: 30, status: 'Cancelled' },
}

/**
 * Insert a meeting for an advisor and client.
 * Custom start time, duration, and status can be supplied when needed.
 */
export function createMeeting(
  advisorId,
  clientId,
  { start = daysFromNow(1), durationMinutes = 30, status = 'Scheduled' } = {},
) {
  if (!advisorId) throw new Error('createMeeting: advisorId is required')

  return executeQuery(
    `INSERT INTO meetings (advisor_id, client_id, meeting_date, duration_minutes, completion_status)
     VALUES ($1, $2, $3, $4, $5::meeting_status)
     RETURNING *`,
    [advisorId, clientId, start, durationMinutes, status],
  )
}

// Tasks

// Preset task data for pending, overdue, and completed scenarios.
export const TASK = {
  pending: { dueDate: dateOnlyFromNow(3), completed: false },
  overdue: { dueDate: dateOnlyFromNow(-2), completed: false },
  done: { dueDate: dateOnlyFromNow(-1), completed: true },
}

// Create a task for an advisor.

export function createTask(
  advisorId,
  {
    title = `E2E Task ${uid()}`,
    dueDate = dateOnlyFromNow(3),
    completed = false,
    clientId = null,
  } = {},
) {
  if (!advisorId) throw new Error('createTask: advisorId is required')

  return executeQuery(
    `INSERT INTO tasks (advisor_id, client_id, task_title, due_date, completed)
     VALUES ($1, $2, $3, $4, $5)
     RETURNING *`,
    [advisorId, clientId, title, dueDate, completed],
  )
}

// Follow-ups

// Preset follow-up configurations for dashboard filtering and status tests.
export const FOLLOW_UP = {
  overdue: { dueDate: dateOnlyFromNow(-3), status: 'Pending' },
  today: { dueDate: dateOnlyFromNow(0), status: 'Pending' },
  upcoming: { dueDate: dateOnlyFromNow(5), status: 'Pending' },
  completedOverdue: { dueDate: dateOnlyFromNow(-4), status: 'Completed' },
  cancelledUpcoming: { dueDate: dateOnlyFromNow(6), status: 'Cancelled' },
}

//Create a follow-up linked to an advisor and client.

export function createFollowUp(
  advisorId,
  clientId,
  {
    reason = `E2E follow-up ${uid()}`,
    stage = 'Financial Needs Analysis',
    dueDate = dateOnlyFromNow(5),
    priority = 'Medium',
    status = 'Pending',
    discussionNotes = null,
  } = {},
) {
  if (!advisorId || !clientId)
    throw new Error('createFollowUp: advisorId and clientId are required')
  return executeQuery(
    `INSERT INTO follow_ups
       (advisor_id, client_id, reason, financial_planning_stage, due_date, priority, status, discussion_notes)
     VALUES ($1, $2, $3, $4::timeline, $5, $6::follow_up_priority, $7::follow_up_status, $8)
     RETURNING *`,
    [advisorId, clientId, reason, stage, dueDate, priority, status, discussionNotes],
  )
}
