import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import '@testing-library/jest-dom/vitest'
import { MemoryRouter } from 'react-router-dom'
import Welcome from '../pages/Welcome'

vi.mock('../assets/orbit-logo.png', () => ({
  default: 'orbit-logo.png',
}))

describe('Welcome Page', () => {
  function renderWelcome() {
    return render(
      <MemoryRouter>
        <Welcome />
      </MemoryRouter>,
    )
  }

  it('renders the main welcome heading', () => {
    renderWelcome()

    expect(
      screen.getByRole('heading', {
        name: /your advisory practice,\s*all in one place/i,

      }),
    ).toBeInTheDocument()
  })

  it('displays the Orbit logo with accessible alt text', () => {
    renderWelcome()

    const logo = screen.getByRole('img', {
      name: 'Orbit logo',
    })

    expect(logo).toBeInTheDocument()
    expect(logo).toHaveAttribute('src', 'orbit-logo.png')
  })

  it('displays the introductory description', () => {
    renderWelcome()

    expect(
      screen.getByText(/centralized platform designed to simplify client management/i),
    ).toBeInTheDocument()
  })

  it('displays the access options heading', () => {
    renderWelcome()

    expect(
      screen.getByRole('heading', {
        name: 'Get started with Orbit',
      }),
    ).toBeInTheDocument()
  })

  it('displays all three access cards', () => {
    renderWelcome()

    expect(screen.getByText('Advisor Login')).toBeInTheDocument()
    expect(screen.getByText('Advisor Registration')).toBeInTheDocument()
    expect(screen.getByText('Public Booking')).toBeInTheDocument()
  })

  it('navigates to the correct routes from each access card', () => {
    const { container } = renderWelcome()

    expect(
      container.querySelector('a[href="/login"]'),
    ).toHaveTextContent('Advisor Login')

    expect(
      container.querySelector('a[href="/create-account"]'),
    ).toHaveTextContent('Advisor Registration')

    expect(
      container.querySelector('a[href="/book-meeting"]'),
    ).toHaveTextContent('Public Booking')
  })

  it('renders the animated orbit background', () => {
    const { container } = renderWelcome()

    const background = container.querySelector('.welcome-sky')

    expect(background).toBeInTheDocument()
    expect(background).toHaveAttribute('aria-hidden', 'true')

    expect(
      background.querySelectorAll('.welcome-track'),
    ).toHaveLength(3)

    expect(
      background.querySelectorAll('.welcome-ring'),
    ).toHaveLength(3)
  })

  it('renders the footer with the current year', () => {
    renderWelcome()

    const currentYear = new Date().getFullYear()

    expect(
      screen.getByText(
        new RegExp(`© ${currentYear} Orbit\\. All rights reserved\\.`),
      ),
    ).toBeInTheDocument()

    expect(
      screen.getByText('Designed for better advisor-client relationships.'),
    ).toBeInTheDocument()
  })
})
