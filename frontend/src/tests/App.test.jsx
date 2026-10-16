import { render, screen } from '@testing-library/react'
import { describe, it, expect } from 'vitest'
import App from '../App' // adjust path depending on where App.test.jsx is relative to App.jsx

describe('App', () => {
  it('renders', () => {
    render(<App />)
    expect(true).toBe(true)
  })
})
