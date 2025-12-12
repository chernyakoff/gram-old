import { useApi } from '@/composables/use-api'
import type { AppSettingIn, LicenseIn, LicenseOut } from '@/types/openapi'

export function useAdmin() {
  const { api, loading, error, success } = useApi()

  async function license(body: LicenseIn) {
    return await api<LicenseOut>(`admin/license`, { method: 'POST', body })
  }

  async function getAppSetting(path: string): Promise<string> {
    return await api(`admin/app-setting/${path}`, { method: 'GET' })
  }

  async function saveAppSetting(body: AppSettingIn): Promise<string> {
    return await api('admin/app-setting', { method: 'POST', body })
  }

  return { license, getAppSetting, saveAppSetting, loading, error, success }
}
