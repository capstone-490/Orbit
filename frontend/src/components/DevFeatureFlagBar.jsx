// 50% or more AI-generated code
import { useState } from 'react'
import { useFeatureFlags } from '../context/useFeatureFlags'

export default function DevFeatureFlagBar() {
  const { serverFlags, devOverrides, setDevOverride, isEnabled } = useFeatureFlags()
  const [open, setOpen] = useState(false)

  const flagNames = Array.from(
    new Set(['use_v2_workspace', ...Object.keys(serverFlags), ...Object.keys(devOverrides)]),
  ).sort()

  if (!open) {
    return (
      <button
        type="button"
        onClick={() => setOpen(true)}
        style={{
          position: 'fixed',
          bottom: 12,
          right: 12,
          zIndex: 9999,
          padding: '6px 10px',
          borderRadius: 6,
          background: '#111827',
          color: '#fff',
          fontSize: 12,
          border: 'none',
          cursor: 'pointer',
        }}
      >
        Flags ({isEnabled('use_v2_workspace') ? 'v2' : 'v1'})
      </button>
    )
  }

  return (
    <aside
      style={{
        position: 'fixed',
        bottom: 12,
        right: 12,
        zIndex: 9999,
        width: 260,
        padding: 12,
        borderRadius: 8,
        background: '#111827',
        color: '#f9fafb',
        fontSize: 12,
        boxShadow: '0 8px 24px rgba(0,0,0,0.3)',
      }}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8 }}>
        <strong>Dev Flags</strong>
        <button
          type="button"
          onClick={() => setOpen(false)}
          style={{ color: '#9ca3af', background: 'none', border: 'none', cursor: 'pointer' }}
        >
          ✕
        </button>
      </div>
      {flagNames.map((name) => {
        const active = isEnabled(name)
        const hasOverride = name in devOverrides
        return (
          <div
            key={name}
            style={{
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              padding: '4px 0',
            }}
          >
            <span>
              {name} {hasOverride ? '(local)' : ''}
            </span>
            <div style={{ display: 'flex', gap: 4 }}>
              <button type="button" onClick={() => setDevOverride(name, !active)}>
                {active ? 'ON' : 'OFF'}
              </button>
              {hasOverride && (
                <button
                  type="button"
                  onClick={() => setDevOverride(name, null)}
                  title="Reset to DB value"
                >
                  ↺
                </button>
              )}
            </div>
          </div>
        )
      })}
    </aside>
  )
}
