import { useApi } from '@/composables/use-api'
import type { CallbackFormIn } from '@/types/openapi'

export function useForms() {
  const { api, loading, error, success } = useApi()

  async function sendCallback(body: CallbackFormIn) {
    return await api(`form/callback`, { method: 'POST', body })
  }

  return {
    sendCallback,
    loading,
    error,
    success,
  }
}
