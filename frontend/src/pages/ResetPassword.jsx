import { useEffect, useState } from 'react'
import { FiArrowRight, FiEye, FiEyeOff, FiLock } from 'react-icons/fi'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import orbitLogo from '../assets/orbit-logo.png'
import { resetPassword, validateResetToken } from '../services/AuthApi.passwordReset'
import '../styles/Login.css'
import '../styles/CreateAccount.css'

function ResetPassword() {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const token = searchParams.get('token') ?? ''

  // 'checking' | 'valid' | 'invalid'
  const [tokenStatus, setTokenStatus] = useState(token ? 'checking' : 'invalid')
  const [tokenError, setTokenError] = useState(
    token ? '' : 'This reset link is invalid or has expired.',
  )

  const [password, setPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [showConfirmPassword, setShowConfirmPassword] = useState(false)

  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState(false)

  useEffect(() => {
    if (!token) return undefined

    let cancelled = false

    validateResetToken(token)
      .then(() => {
        if (!cancelled) setTokenStatus('valid')
      })
      .catch((validationError) => {
        if (cancelled) return
        setTokenStatus('invalid')
        setTokenError(
          validationError instanceof Error
            ? validationError.message
            : 'This reset link is invalid or has expired.',
        )
      })

    return () => {
      cancelled = true
    }
  }, [token])

  async function handleSubmit(event) {
    event.preventDefault()
    setError('')

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
      await resetPassword({ token, password })
      setSuccess(true)
      setPassword('')
      setConfirmPassword('')
    } catch (resetError) {
      const message =
        resetError instanceof Error
          ? resetError.message
          : 'Unable to reset your password. Please try again.'

      // A consumed or expired token cannot be retried; show the dedicated state.
      if (/invalid or has expired/i.test(message)) {
        setTokenStatus('invalid')
        setTokenError(message)
      } else {
        setError(message)
      }
    } finally {
      setIsLoading(false)
    }
  }

  function renderCardContent() {
    if (success) {
      return (
        <div className="registration-success" role="status">
          <h2>Password reset successfully!</h2>
          <p>Your password has been updated. You can now sign in with your new password.</p>

          <button type="button" className="login-submit" onClick={() => navigate('/login')}>
            Go to Sign In
            <FiArrowRight aria-hidden="true" />
          </button>
        </div>
      )
    }

    if (tokenStatus === 'checking') {
      return (
        <p role="status" className="registration-hint">
          Verifying your reset link...
        </p>
      )
    }

    if (tokenStatus === 'invalid') {
      return (
        <div className="registration-success" role="alert">
          <h2>Link not valid</h2>
          <p>{tokenError}</p>

          <Link to="/forgot-password" className="login-submit">
            Request a new link
            <FiArrowRight aria-hidden="true" />
          </Link>
        </div>
      )
    }

    return (
      <form onSubmit={handleSubmit}>
        <div className="login-field">
          <label htmlFor="reset-password">New Password</label>
          <div className="login-input-wrap">
            <FiLock aria-hidden="true" />
            <input
              id="reset-password"
              name="password"
              type={showPassword ? 'text' : 'password'}
              autoComplete="new-password"
              placeholder="Create a new password"
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
          <label htmlFor="reset-confirm-password">Confirm New Password</label>
          <div className="login-input-wrap">
            <FiLock aria-hidden="true" />
            <input
              id="reset-confirm-password"
              name="confirmPassword"
              type={showConfirmPassword ? 'text' : 'password'}
              autoComplete="new-password"
              placeholder="Confirm your new password"
              value={confirmPassword}
              onChange={(event) => setConfirmPassword(event.target.value)}
              required
            />

            <button
              type="button"
              className="password-toggle"
              aria-label={
                showConfirmPassword ? 'Hide confirmation password' : 'Show confirmation password'
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
          {isLoading ? 'Resetting password...' : 'Reset Password'}
          {!isLoading && <FiArrowRight aria-hidden="true" />}
        </button>
      </form>
    )
  }

  return (
    <main className="login-page">
      <div className="login-orbit login-orbit-one" />
      <div className="login-orbit login-orbit-two" />
      <span className="login-dot login-dot-one" />
      <span className="login-dot login-dot-two" />
      <span className="login-dot login-dot-three" />

      <section className="login-shell" aria-labelledby="reset-password-title">
        <div className="login-brand">
          <div className="login-logo-frame">
            <img src={orbitLogo} alt="Orbit" />
          </div>

          <h1 id="reset-password-title">Reset your password</h1>
          <p>Choose a new password for your Orbit account.</p>
        </div>

        <div className="login-card">{renderCardContent()}</div>
      </section>
    </main>
  )
}

export default ResetPassword
