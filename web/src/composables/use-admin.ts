import { useApi } from '@/composables/use-api'
import type { LicenseIn, LicenseOut } from '@/types/openapi'

export function useAdmin() {
  const { api, loading, error, success } = useApi()

  async function license(body: LicenseIn) {
    return await api<LicenseOut>(`admin/license`, { method: 'POST', body })
  }

  return { license, loading, error, success }
}
