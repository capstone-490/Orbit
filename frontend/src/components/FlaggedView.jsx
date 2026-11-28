import { Suspense } from 'react'
import { useFeatureFlag } from '../context/useFeatureFlags'

export function FlaggedView({
  flag,
  v1: V1Component,
  v2: V2Component,
  fallback = <p>Loading...</p>,
}) {
  const { enabled, loading } = useFeatureFlag(flag)
  if (loading) return fallback
  const Active = enabled ? V2Component : V1Component
  return (
    <Suspense fallback={fallback}>
      <Active />
    </Suspense>
  )
}
