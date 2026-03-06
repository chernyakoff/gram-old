import { useApi } from '@/composables/use-api'
import type {
  AppSettingIn,
  BalanceIn,
  BalanceOut,
  GetBalanceOut,
  LicenseIn,
  LicenseOut,
} from '@/types/openapi'

export function useAdmin() {
  const { api, loading, error, success } = useApi()

  async function license(body: LicenseIn) {
    return await api<LicenseOut>(`admin/license`, { method: 'POST', body })
  }

  async function addBalance(body: BalanceIn): Promise<BalanceOut> {
    return await api<BalanceOut>(`admin/balance`, { method: 'POST', body })
  }

  async function getBalance(): Promise<GetBalanceOut> {
    return await api<GetBalanceOut>(`admin/balance`, { method: 'GET' })
  }

  async function getAppSetting(path: string): Promise<string> {
    return await api(`admin/app-setting/${path}`, { method: 'GET' })
  }

  async function saveAppSetting(body: AppSettingIn): Promise<string> {
    return await api('admin/app-setting', { method: 'POST', body })
  }

  return { license, getAppSetting, saveAppSetting, addBalance, getBalance, loading, error, success }
}
