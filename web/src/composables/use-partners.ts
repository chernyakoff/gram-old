import { useApi } from '@/composables/use-api'
import type { PartnerOut } from '@/types/openapi'

export function usePartners() {
  const { api, loading, error, success } = useApi()

  
  async function getPartners(): Promise<PartnerOut> {
    return await api<PartnerOut>(`partners`, { method: 'GET' })
  }


  return {
    getPartners,
    loading,
    error,
    success,
  }
}
