// Substantial AI assistance used; verified with frontend tests.
import { useCallback, useEffect, useRef, useState } from 'react'
import { updateFollowUp, updateFollowUpStatus } from '../services/FollowUpsApi'
import {
  getFollowUp,
  getPriorityActionSuggestions,
  getPriorityActions,
} from '../services/PriorityActionsApi'

// AI suggestions are slow to generate, so they are kept for the browser
// session (sessionStorage is cleared when the tab is closed). The cache is
// only reused when the urgent follow-up list is unchanged and recent enough.
export const SUGGESTION_CACHE_KEY = 'orbit.priorityActions.aiSuggestions'
export const SUGGESTION_CACHE_TTL_MS = 10 * 60 * 1000

function readCache() {
  try {
    const raw = window.sessionStorage.getItem(SUGGESTION_CACHE_KEY)
    return raw ? JSON.parse(raw) : null
  } catch {
    return null
  }
}

function writeCache(value) {
  try {
    window.sessionStorage.setItem(SUGGESTION_CACHE_KEY, JSON.stringify(value))
  } catch {
    // Storage can be full or blocked; suggestions still work without caching.
  }
}

function updateCache(change) {
  const cached = readCache()
  if (cached) writeCache(change(cached))
}

const sortedIds = (actions) =>
  actions.map((action) => action.follow_up_id).sort((first, second) => first - second)

const sameIds = (first, second) =>
  first.length === second.length && first.every((id, index) => id === second[index])

// Loads urgent follow-ups and AI suggestions. A slow or failing AI call never
// delays or breaks the urgent list.
export function usePriorityActions(limit = 5) {
  const [actions, setActions] = useState([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [aiStatus, setAiStatus] = useState('loading')
  const [suggestions, setSuggestions] = useState([])
  const [reloadKey, setReloadKey] = useState(0)
  const [suggestionsKey, setSuggestionsKey] = useState(0)
  const forceRefresh = useRef(false)

  useEffect(() => {
    let active = true

    const loadActions = async () => {
      if (active) {
        setLoading(true)
        setError('')
      }
      try {
        const data = await getPriorityActions(limit)
        if (active) {
          setActions(data.items ?? [])
          setTotal(data.total ?? 0)
        }
      } catch (err) {
        console.error('Failed to load priority actions:', err)
        if (active) setError('Could not load urgent follow-ups.')
      } finally {
        if (active) setLoading(false)
      }
    }

    void loadActions()
    return () => {
      active = false
    }
  }, [limit, reloadKey])

  const actionIdsKey = sortedIds(actions).join(',')

  useEffect(() => {
    if (loading) return undefined

    let active = true
    const actionIds = actionIdsKey ? actionIdsKey.split(',').map(Number) : []
    const force = forceRefresh.current
    forceRefresh.current = false

    const loadSuggestions = async () => {
      if (error) {
        if (active) {
          setAiStatus('unavailable')
          setSuggestions([])
        }
        return
      }

      const cached = readCache()
      const cacheIsUsable =
        !force &&
        cached &&
        Date.now() - cached.savedAt < SUGGESTION_CACHE_TTL_MS &&
        sameIds(cached.actionIds, actionIds)

      if (cacheIsUsable) {
        if (active) {
          setAiStatus(cached.status)
          setSuggestions(cached.suggestions)
        }
        return
      }

      // Follow-ups whose suggestion was dismissed or approved this session stay
      // hidden when suggestions are regenerated, unless the advisor refreshes.
      const handledIds = force ? [] : (cached?.handledIds ?? [])

      if (active) setAiStatus('loading')
      try {
        const data = await getPriorityActionSuggestions()
        if (!active) return
        const status = data.status ?? 'unavailable'
        const fresh = (data.suggestions ?? []).filter(
          (suggestion) => !handledIds.includes(suggestion.follow_up_id),
        )
        setAiStatus(status)
        setSuggestions(fresh)
        if (status === 'available') {
          writeCache({ savedAt: Date.now(), actionIds, status, suggestions: fresh, handledIds })
        }
      } catch (err) {
        console.error('Failed to load AI suggestions:', err)
        if (active) {
          setAiStatus('unavailable')
          setSuggestions([])
        }
      }
    }

    void loadSuggestions()
    return () => {
      active = false
    }
  }, [loading, error, actionIdsKey, suggestionsKey])

  const retry = useCallback(() => setReloadKey((key) => key + 1), [])

  // Asks the AI for new suggestions, ignoring the cache.
  const refreshSuggestions = useCallback(() => {
    forceRefresh.current = true
    setSuggestionsKey((key) => key + 1)
  }, [])

  // Marks a follow-up Completed and removes it (and its suggestion) from the
  // dashboard without regenerating the other suggestions.
  // Throws if the update fails so the caller can show an error.
  const completeAction = useCallback(async (followUpId) => {
    await updateFollowUpStatus(followUpId, 'Completed')
    updateCache((cached) => ({
      ...cached,
      actionIds: cached.actionIds.filter((id) => id !== followUpId),
      suggestions: cached.suggestions.filter((suggestion) => suggestion.follow_up_id !== followUpId),
    }))
    setActions((current) => current.filter((action) => action.follow_up_id !== followUpId))
    setSuggestions((current) =>
      current.filter((suggestion) => suggestion.follow_up_id !== followUpId),
    )
    setTotal((current) => Math.max(0, current - 1))
  }, [])

  // Approving saves the AI suggestion into the follow-up's discussion notes,
  // appended after any existing notes. Throws if saving fails.
  const approveSuggestion = useCallback(async (followUpId, text) => {
    const followUp = await getFollowUp(followUpId)
    const note = `AI-suggested next step (approved): ${text}`
    const existingNotes = (followUp.discussion_notes ?? '').trim()
    await updateFollowUp(followUpId, {
      discussion_notes: existingNotes ? `${existingNotes}\n\n${note}` : note,
    })
    const markApproved = (list) =>
      list.map((suggestion) =>
        suggestion.follow_up_id === followUpId ? { ...suggestion, approved: true } : suggestion,
      )
    updateCache((cached) => ({
      ...cached,
      suggestions: markApproved(cached.suggestions),
      handledIds: [...new Set([...cached.handledIds, followUpId])],
    }))
    setSuggestions(markApproved)
  }, [])

  // Dismissing hides the suggestion for the rest of the browser session.
  const dismissSuggestion = useCallback((followUpId) => {
    const withoutDismissed = (list) =>
      list.filter((suggestion) => suggestion.follow_up_id !== followUpId)
    updateCache((cached) => ({
      ...cached,
      suggestions: withoutDismissed(cached.suggestions),
      handledIds: [...new Set([...cached.handledIds, followUpId])],
    }))
    setSuggestions(withoutDismissed)
  }, [])

  return {
    actions,
    total,
    loading,
    error,
    retry,
    completeAction,
    aiStatus,
    suggestions,
    refreshSuggestions,
    approveSuggestion,
    dismissSuggestion,
  }
}