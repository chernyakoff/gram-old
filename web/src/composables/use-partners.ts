import { useApi } from '@/composables/use-api'
import type { PartnerOut } from '@/types/openapi-users'

export function usePartners() {
  const { apiUsers, loading, error, success } = useApi()

  async function getPartners(): Promise<PartnerOut> {
    return await apiUsers<PartnerOut>('partners/', { method: 'GET' })
  }

  return {
    getPartners,
    loading,
    error,
    success,
  }
}
