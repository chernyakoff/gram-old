import { useApi } from '@/composables/use-api'
import type { SettingsIn, SettingsOut } from '@/types/openapi'

export function useSettings() {
  const { api, loading, error, success } = useApi()

  async function get(): Promise<SettingsOut> {
    return await api<SettingsOut>('settings', {
      method: 'GET',
    })
  }

  async function save(body: SettingsIn): Promise<SettingsOut> {
    return await api<SettingsOut>('settings', {
      method: 'POST',
      body,
    })
  }

  return { get, save, loading, error, success }
}
