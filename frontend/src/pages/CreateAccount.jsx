// Substantial AI assistance used; verified with frontend tests and production build.
import { useState } from 'react'
import { FiArrowRight, FiEye, FiEyeOff, FiLock, FiMail, FiUser } from 'react-icons/fi'
import { Link, useNavigate } from 'react-router-dom'
import orbitLogo from '../assets/orbit-logo.png'
import { registerAdvisor } from '../services/AuthApi'
import '../styles/Login.css'
import '../styles/CreateAccount.css'

function CreateAccount() {
  const navigate = useNavigate()

  const [username, setUsername] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')

  const [showPassword, setShowPassword] = useState(false)
  const [showConfirmPassword, setShowConfirmPassword] = useState(false)

  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState(false)

  async function handleSubmit(event) {
    event.preventDefault()
    setError('')

    if (!username.trim()) {
      setError('Please enter a username.')
      return
    }

    if (username.trim().length > 100) {
      setError('Username must be 100 characters or fewer.')
      return
    }

    if (password.length < 12 || password.length > 128) {
      setError('Password must be between 12 and 128 characters.')
      return
    }

    if (password !== confirmPassword) {
      setError('Passwords do not match.')
      return
    }

    setIsLoading(true)

    try {
      await registerAdvisor({
        username: username.trim(),
        email: email.trim().toLowerCase(),
        password,
      })

      setSuccess(true)
      setPassword('')
      setConfirmPassword('')
    } catch (registrationError) {
      setError(
        registrationError instanceof Error
          ? registrationError.message
          : 'Unable to create your account. Please try again.',
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

      <section className="login-shell" aria-labelledby="registration-title">
        <div className="login-brand">
          <div className="login-logo-frame">
            <img src={orbitLogo} alt="Orbit" />
          </div>

          <h1 id="registration-title">Create your account</h1>
          <p>
            Join Orbit to manage your workspace,
            <br />
            clients, and workflows.
          </p>
        </div>

        <div className="login-card">
          {success ? (
            <div className="registration-success" role="status">
              <h2>Account created successfully!</h2>
              <p>Your advisor account is ready. You can now sign in.</p>

              <button type="button" className="login-submit" onClick={() => navigate('/login')}>
                Go to Sign In
                <FiArrowRight aria-hidden="true" />
              </button>
            </div>
          ) : (
            <>
              <form onSubmit={handleSubmit}>
                <div className="login-field">
                  <label htmlFor="registration-username">Username</label>
                  <div className="login-input-wrap">
                    <FiUser aria-hidden="true" />
                    <input
                      id="registration-username"
                      name="username"
                      type="text"
                      autoComplete="username"
                      placeholder="Enter your username"
                      maxLength={100}
                      value={username}
                      onChange={(event) => setUsername(event.target.value)}
                      required
                    />
                  </div>
                </div>

                <div className="login-field">
                  <label htmlFor="registration-email">Email</label>
                  <div className="login-input-wrap">
                    <FiMail aria-hidden="true" />
                    <input
                      id="registration-email"
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
                  <label htmlFor="registration-password">Password</label>
                  <div className="login-input-wrap">
                    <FiLock aria-hidden="true" />
                    <input
                      id="registration-password"
                      name="password"
                      type={showPassword ? 'text' : 'password'}
                      autoComplete="new-password"
                      placeholder="Create a password"
                      minLength={12}
                      maxLength={128}
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
                      {showPassword ? <FiEye /> : <FiEyeOff />}
                    </button>
                  </div>
                  <p className="registration-hint">Use between 12 and 128 characters.</p>
                </div>

                <div className="login-field">
                  <label htmlFor="registration-confirm-password">Confirm Password</label>
                  <div className="login-input-wrap">
                    <FiLock aria-hidden="true" />
                    <input
                      id="registration-confirm-password"
                      name="confirmPassword"
                      type={showConfirmPassword ? 'text' : 'password'}
                      autoComplete="new-password"
                      placeholder="Confirm your password"
                      value={confirmPassword}
                      onChange={(event) => setConfirmPassword(event.target.value)}
                      required
                    />

                    <button
                      type="button"
                      className="password-toggle"
                      aria-label={
                        showConfirmPassword
                          ? 'Hide confirmation password'
                          : 'Show confirmation password'
                      }
                      onClick={() => setShowConfirmPassword((visible) => !visible)}
                    >
                      {showConfirmPassword ? <FiEye /> : <FiEyeOff />}
                    </button>
                  </div>
                </div>

                {error && (
                  <p className="login-error" role="alert">
                    {error}
                  </p>
                )}

                <button type="submit" className="login-submit" disabled={isLoading}>
                  {isLoading ? 'Creating account...' : 'Create Account'}
                  {!isLoading && <FiArrowRight aria-hidden="true" />}
                </button>
              </form>

              <p className="create-account">
                Already have an account? <Link to="/login">Sign in</Link>
              </p>
            </>
          )}
        </div>
      </section>
    </main>
  )
}

export default CreateAccount
