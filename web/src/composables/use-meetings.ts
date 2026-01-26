import { useApi } from '@/composables/use-api'
import type { MeetingOut } from '@/types/openapi'

export function useMeetings() {
  const { api, loading, error, success } = useApi()

  async function getMonthMeetings(year: number, month: number) {
    return await api<{ date: string; count: number }[]>('meetings', {
      method: 'GET',
      searchParams: {
        year,
        month,
      },
    })
  }

  async function getDayMeetings(date: string): Promise<MeetingOut[]> {
    return await api<MeetingOut[]>('meetings/day', {
      method: 'GET',
      searchParams: {
        date, // YYYY-MM-DD
      },
    })
  }

  return { getMonthMeetings, getDayMeetings, loading, error, success }
}
