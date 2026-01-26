import { useApi } from '@/composables/use-api'
import type { MeetingDuration, UserTimezone } from '@/types/openapi'

export function useProfile() {
  const { api, loading, error, success } = useApi()

  async function saveMeetingDuration(body: MeetingDuration) {
    return await api(`profile/meeting-duration`, { method: 'POST', body })
  }

  async function saveTimezone(body: UserTimezone) {
    return await api(`profile/timezone`, { method: 'POST', body })
  }

  return { saveMeetingDuration, saveTimezone, loading, error, success }
}
