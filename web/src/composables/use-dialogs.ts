import { useApi } from '@/composables/use-api'

import type { DialogIn, DialogMessageOut, DialogOut, DialogSystemMessageIn } from '@/types/openapi'
import { ref } from 'vue'

export function useDialogs() {
  const dialogs = ref<DialogOut[]>([])
  const { api, loading, error, success } = useApi()

  async function list(body: DialogIn): Promise<DialogOut[]> {
    const data = await api<DialogOut[]>('dialogs', { method: 'POST', body })
    dialogs.value = data
    return data
  }

  async function get(id: number): Promise<DialogMessageOut[]> {
    return await api<DialogMessageOut[]>(`dialogs/${id}`, { method: 'GET' })
  }

  async function add(body: DialogSystemMessageIn) {
    return await api<DialogMessageOut[]>('dialogs/add', { method: 'POST', body })
  }

  return { get, add, list, dialogs, loading, error, success }
}
