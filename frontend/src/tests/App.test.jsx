import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, test, vi } from 'vitest'
import '@testing-library/jest-dom/vitest'
import App from '../App'

vi.mock('../pages/AdvisorDashboard', () => ({
  default: () => <h1>Dashboard page</h1>,
}))

describe('App routes', () => {
  test('renders the shared navigation and navigates to each static page', () => {
    window.history.pushState({}, '', '/')
    render(<App />)

    expect(screen.getByRole('heading', { name: 'Dashboard page' })).toBeInTheDocument()

    const destinations = [
      ['Calendar', 'Calendar'],
      ['Follow-Ups', 'Follow-Ups'],
      ['Tasks', 'Tasks'],
      ['Documents', 'Documents'],
      ['AI Review', 'AI Review'],
      ['Activity', 'Activity'],
    ]

    for (const [linkName, pageName] of destinations) {
      fireEvent.click(screen.getByRole('link', { name: linkName }))
      expect(screen.getByText(pageName)).toBeInTheDocument()
    }

    expect(screen.getByRole('link', { name: 'Dashboard' })).toHaveAttribute('href', '/')
  })
})
