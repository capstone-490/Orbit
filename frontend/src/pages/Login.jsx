// Substantial AI assistance used; verified with frontend tests and production build.
import { useState } from 'react'
import { FiArrowRight, FiEye, FiEyeOff, FiLock, FiMail } from 'react-icons/fi'
import { useNavigate } from 'react-router-dom'
import orbitLogo from '../assets/orbit-logo.png'
import { loginAdvisor } from '../services/AuthApi'
import '../styles/Login.css'

function Login() {
  const navigate = useNavigate()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [rememberDevice, setRememberDevice] = useState(false)
  const [showPassword, setShowPassword] = useState(false)
  const [workspaceType, setWorkspaceType] = useState('advisor')
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState('')

  async function handleSubmit(event) {
    event.preventDefault()
    setError('')
    setIsLoading(true)

    try {
      const result = await loginAdvisor({ email, password })
      if (result?.token) {
        localStorage.setItem('orbit_auth_token', result.token)
      }
      navigate('/dashboard')
    } catch (loginError) {
      setError(
        loginError instanceof Error ? loginError.message : 'Unable to sign in. Please try again.',
      )
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <main className="login-page">
      <div className="login-orbit login-orbit-one" />
      <div className="login-orbit login-orbit-two" />
      <span className="login-dot login-dot-one" />
      <span className="login-dot login-dot-two" />
      <span className="login-dot login-dot-three" />

      <section className="login-shell" aria-labelledby="login-title">
        <div className="login-brand">
          <div className="login-logo-frame">
            <img src={orbitLogo} alt="Orbit" />
          </div>
          <h1 id="login-title">Welcome to Orbit</h1>
          <p>
            Manage your workspace, clients, and
            <br />
            automate workflows.
          </p>
        </div>

        <div className="login-card">
          <div className="login-tabs" role="tablist" aria-label="Workspace type">
            <button
              type="button"
              className={`login-tab ${workspaceType === 'advisor' ? 'login-tab-active' : ''}`}
              role="tab"
              aria-selected={workspaceType === 'advisor'}
              onClick={() => setWorkspaceType('advisor')}
            >
              Advisor Workspace
            </button>
            <button
              type="button"
              className={`login-tab ${workspaceType === 'meeting' ? 'login-tab-active' : ''}`}
              role="tab"
              aria-selected={workspaceType === 'meeting'}
              onClick={() => setWorkspaceType('meeting')}
            >
              Book A Meeting
            </button>
          </div>

          <form onSubmit={handleSubmit} noValidate>
            <div className="login-field">
              <label htmlFor="email">Email</label>
              <div className="login-input-wrap">
                <FiMail aria-hidden="true" />
                <input
                  id="email"
                  name="email"
                  type="email"
                  autoComplete="email"
                  placeholder="you@example.com"
                  value={email}
                  onChange={(event) => setEmail(event.target.value)}
                  required
                />
              </div>
            </div>

            <div className="login-field">
              <div className="login-label-row">
                <label htmlFor="password">Password</label>
                <button type="button" className="forgot-password">
                  Forgot?
                </button>
              </div>
              <div className="login-input-wrap">
                <FiLock aria-hidden="true" />
                <input
                  id="password"
                  name="password"
                  type={showPassword ? 'text' : 'password'}
                  autoComplete="current-password"
                  placeholder="Enter your password"
                  value={password}
                  onChange={(event) => setPassword(event.target.value)}
                  required
                />
                <button
                  type="button"
                  className="password-toggle"
                  aria-label={showPassword ? 'Hide password' : 'Show password'}
                  onClick={() => setShowPassword((visible) => !visible)}
                >
                  {showPassword ? <FiEyeOff aria-hidden="true" /> : <FiEye aria-hidden="true" />}
                </button>
              </div>
            </div>

            <label className="remember-device">
              <input
                type="checkbox"
                checked={rememberDevice}
                onChange={(event) => setRememberDevice(event.target.checked)}
              />
              <span className="remember-switch" aria-hidden="true" />
              Remember this device
            </label>

            {error && (
              <p className="login-error" role="alert">
                {error}
              </p>
            )}

            <button type="submit" className="login-submit" disabled={isLoading}>
              {isLoading ? 'Signing in...' : 'Sign In'}
              {!isLoading && <FiArrowRight aria-hidden="true" />}
            </button>
          </form>

          <p className="create-account">
            Don&apos;t have an account? <a href="/contact">Create an account</a>
          </p>
        </div>
      </section>
    </main>
  )
}

export default Login
