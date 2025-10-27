import { ref } from 'vue'

import { useApi } from '@/composables/use-api'
import type { MailingListOut, MailingOut } from '@/types/openapi'
import type { MailingFormSchema } from '@/schemas/mailings'

export function useMailings() {
  const mailings = ref<MailingOut[]>([])
  const { api, loading, error, success } = useApi()

  async function del(ids: number[]) {
    const query = ids.map((id) => `id=${id}`).join('&')
    return await api(`mailings?${query}`, { method: 'DELETE' })
  }

  async function get(): Promise<MailingOut[]> {
    const data = await api<MailingOut[]>('mailings', {
      method: 'GET',
    })
    mailings.value = data
    return data
  }

  async function create(data: MailingFormSchema): Promise<void> {
    return await api('mailings', {
      method: 'POST',
      body: data,
    })
  }

  async function list() {
    return await api<MailingListOut[]>('mailings/list', { method: 'GET' })
  }

  return { create, get, del, list, mailings, loading, error, success }
}
