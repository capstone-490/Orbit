import { useState } from 'react'
import { FiArrowRight, FiMail } from 'react-icons/fi'
import { Link } from 'react-router-dom'
import orbitLogo from '../assets/orbit-logo.png'
import { requestPasswordReset } from '../services/AuthApi.passwordReset'
import '../styles/Login.css'
import '../styles/CreateAccount.css'
import AnimatedOrbitBackground from '../components/AnimatedOrbitBackground/AnimatedOrbitBackground'

const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]+$/

function ForgotPassword() {
  const [email, setEmail] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState(false)

  async function handleSubmit(event) {
    event.preventDefault()
    setError('')

    const normalizedEmail = email.trim().toLowerCase()

    if (!normalizedEmail) {
      setError('Please enter your email address.')
      return
    }

    if (!EMAIL_PATTERN.test(normalizedEmail)) {
      setError('Please enter a valid email address.')
      return
    }

    setIsLoading(true)

    try {
      await requestPasswordReset({ email: normalizedEmail })
      setSuccess(true)
    } catch (requestError) {
      setError(
        requestError instanceof Error
          ? requestError.message
          : 'Unable to send the reset link. Please try again.',
      )
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <main className="login-page forgot-password-page">  
      <AnimatedOrbitBackground />
      <section className="login-shell forgot-password-shell" aria-labelledby="forgot-password-title">
        <div className="login-brand">
          <div className="login-logo-frame">
            <img src={orbitLogo} alt="Orbit" />
          </div>

          <h1 id="forgot-password-title">Forgot your password?</h1>
          <p>
            Enter your email and we'll send you
            <br />a link to reset it.
          </p>
        </div>

        <div className="login-card">
          {success ? (
            <div className="registration-success" role="status">
              <h2>Check your email</h2>
              <p>
                If an account exists for {email.trim().toLowerCase()}, a password reset link is on
                its way. The link expires in 30 minutes.
              </p>

              <Link to="/login" className="login-submit">
                Back to Sign In
                <FiArrowRight aria-hidden="true" />
              </Link>
            </div>
          ) : (
            <>
              <form onSubmit={handleSubmit} noValidate>
                <div className="login-field">
                  <label htmlFor="forgot-email">Email</label>
                  <div className="login-input-wrap">
                    <FiMail aria-hidden="true" />
                    <input
                      id="forgot-email"
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

                {error && (
                  <p className="login-error" role="alert">
                    {error}
                  </p>
                )}

                <button type="submit" className="login-submit" disabled={isLoading}>
                  {isLoading ? 'Sending link...' : 'Send Reset Link'}
                  {!isLoading && <FiArrowRight aria-hidden="true" />}
                </button>
              </form>

              <p className="create-account">
                Remembered it? <Link to="/login">Sign in</Link>
              </p>
            </>
          )}
        </div>
      </section>
    </main>
  )
}

export default ForgotPassword
