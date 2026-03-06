import type { UserTimezone } from '@/types/openapi'
import { useApi } from './use-api'
import TIMEZONES from '@/utils/timezones.json'

export const useTimezones = () => {
  const { api } = useApi()

  async function loadTimezone(): Promise<string> {
    return await api<string>(`profile/timezone`, { method: 'GET' })
  }

  async function saveTimezone(body: UserTimezone): Promise<void> {
    return await api(`profile/timezone`, { method: 'POST', body })
  }

  return { timezones: TIMEZONES, loadTimezone, saveTimezone }
}
