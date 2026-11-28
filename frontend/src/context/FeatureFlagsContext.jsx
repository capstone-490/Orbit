// 50% or more AI-generated code
import { useCallback, useEffect, useMemo, useState } from 'react'
import { FeatureFlagsContext } from './useFeatureFlags'

const API_V2_BASE = import.meta.env.VITE_API_V2_URL || 'http://127.0.0.1:8001/api/v2'
const DEV_STORAGE_KEY = 'orbit_dev_flag_overrides'

function readStoredOverrides() {
  try {
    const parsed = JSON.parse(localStorage.getItem(DEV_STORAGE_KEY) || '{}')
    return parsed && typeof parsed === 'object' ? parsed : {}
  } catch {
    return {}
  }
}

function readDevOverrides() {
  if (!import.meta.env.DEV) return {}
  const overrides = { ...readStoredOverrides() }
  const params = new URLSearchParams(window.location.search)
  for (const [key, val] of params.entries()) {
    if (key.startsWith('ff_')) {
      overrides[key.slice(3)] = val === '1' || val.toLowerCase() === 'true'
    }
  }
  return overrides
}

export function FeatureFlagsProvider({ children }) {
  const [serverFlags, setServerFlags] = useState({})
  const [devOverrides, setDevOverrides] = useState(readDevOverrides)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let active = true
    fetch(`${API_V2_BASE}/feature-flags`)
      .then((res) => (res.ok ? res.json() : null))
      .then((data) => {
        if (active && data?.flags) setServerFlags(data.flags)
      })
      .catch(() => {})
      .finally(() => {
        if (active) setLoading(false)
      })
    return () => {
      active = false
    }
  }, [])

  const setDevOverride = useCallback((name, value) => {
    if (!import.meta.env.DEV) return
    setDevOverrides((prev) => {
      const next = { ...prev }
      if (value === null) {
        delete next[name]
      } else {
        next[name] = Boolean(value)
      }
      localStorage.setItem(DEV_STORAGE_KEY, JSON.stringify(next))
      return next
    })
  }, [])

  const value = useMemo(
    () => ({
      loading,
      serverFlags,
      devOverrides,
      setDevOverride,
      isEnabled: (name, fallback = false) => {
        if (import.meta.env.DEV && name in devOverrides) {
          return Boolean(devOverrides[name])
        }
        return serverFlags[name] ?? fallback
      },
    }),
    [loading, serverFlags, devOverrides, setDevOverride],
  )

  return <FeatureFlagsContext.Provider value={value}>{children}</FeatureFlagsContext.Provider>
}
