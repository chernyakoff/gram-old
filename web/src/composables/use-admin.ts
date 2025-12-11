import { useApi } from '@/composables/use-api'
import type { ImpersonateIn, ImpersonateOut, LicenseIn, LicenseOut } from '@/types/openapi'

export function useAdmin() {
  const { api, loading, error, success } = useApi()

  async function license(body: LicenseIn) {
    return await api<LicenseOut>(`admin/license`, { method: 'POST', body })
  }

   async function impersonate(body: ImpersonateIn) {
    return await api<ImpersonateOut>(`admin/impersonate`, { method: 'POST', body })
  }
     async function stopImpersonate() {
    return await api(`admin/stop-impersonate`, { method: 'POST' })
  }


  return { license, stopImpersonate, impersonate, loading, error, success }
}
