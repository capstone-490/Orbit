import { createContext, useContext } from 'react'

export const FeatureFlagsContext = createContext(null)

export function useFeatureFlags() {
  const ctx = useContext(FeatureFlagsContext)
  if (!ctx) {
    throw new Error('useFeatureFlags must be used inside FeatureFlagsProvider')
  }
  return ctx
}

export function useFeatureFlag(name, fallback = false) {
  const { isEnabled, loading } = useFeatureFlags()
  return { enabled: isEnabled(name, fallback), loading }
}
