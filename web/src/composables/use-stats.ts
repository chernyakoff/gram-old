import { useApi } from '@/composables/use-api'

import type { StatsIn, StatsOut } from '@/types/openapi'

export function useStats() {
  const { api, loading, error, success } = useApi()

  async function getStats(body: StatsIn): Promise<StatsOut> {
    return await api<StatsOut>('stats', { method: 'POST', body })
  }

  return {
    getStats,

    loading,
    error,
    success,
  }
}
