import { useStorage } from '@vueuse/core'

type PremiumPendingReason = 'purchase' | 'verification'

type PremiumPendingEntry = {
  until: number // epoch ms
  reason: PremiumPendingReason
}

type PremiumPendingMap = Record<string, PremiumPendingEntry>

const STORAGE_KEY = 'premium-pending-by-account'

function formatRemaining(ms: number) {
  const totalSec = Math.max(0, Math.ceil(ms / 1000))
  const min = Math.floor(totalSec / 60)
  const sec = totalSec % 60
  if (min <= 0) return `${sec}s`
  return sec ? `${min}m ${sec}s` : `${min}m`
}

export function usePremiumPending() {
  const pendingByAccount = useStorage<PremiumPendingMap>(STORAGE_KEY, {})

  function clearPending(accountId: number) {
    const key = String(accountId)
    if (!(key in pendingByAccount.value)) return
     
    delete pendingByAccount.value[key]
  }

  function getPending(accountId: number): PremiumPendingEntry | null {
    const key = String(accountId)
    const entry = pendingByAccount.value[key]
    if (!entry) return null
    if (entry.until <= Date.now()) {
      clearPending(accountId)
      return null
    }
    return entry
  }

  function isPending(accountId: number) {
    return !!getPending(accountId)
  }

  function remainingLabel(accountId: number) {
    const entry = getPending(accountId)
    if (!entry) return null
    return formatRemaining(entry.until - Date.now())
  }

  function setPending(accountId: number, minutes: number, reason: PremiumPendingReason) {
    pendingByAccount.value[String(accountId)] = {
      until: Date.now() + minutes * 60_000,
      reason,
    }
  }

  return {
    setPending,
    clearPending,
    getPending,
    isPending,
    remainingLabel,
  }
}

