import { useApi } from '@/composables/use-api'

import type { DialogMessageOut, DialogOut } from '@/types/openapi'
import { ref } from 'vue'

export function useDialogs() {
  const dialogs = ref<DialogOut[]>([])
  const { api, loading, error, success } = useApi()

  async function get(): Promise<DialogOut[]>
  async function get(id: number): Promise<DialogMessageOut[]>
  async function get(id?: number) {
    if (id) {
      return await api<DialogMessageOut[]>(`dialogs/${id}`, { method: 'GET' })
    } else {
      const data = await api<DialogOut[]>('dialogs', { method: 'GET' })
      dialogs.value = data
      return data
    }
  }

  return { get, dialogs, loading, error, success }
}
