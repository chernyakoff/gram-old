import { useApi } from '@/composables/use-api'

import type { PromptIn, PromptOut } from '@/types/openapi'
import { ref } from 'vue'

export function usePrompts() {
  const prompts = ref<PromptOut[]>([])
  const { api, loading, error, success } = useApi()

  async function del(ids: number[]) {
    const query = ids.map((id) => `id=${id}`).join('&')
    return await api(`prompts?${query}`, { method: 'DELETE' })
  }

  async function get(): Promise<PromptOut[]>
  async function get(id: number): Promise<PromptOut>
  async function get(id?: number) {
    if (id) {
      return await api<PromptOut>(`prompts/${id}`, { method: 'GET' })
    } else {
      const data = await api<PromptOut[]>('prompts', { method: 'GET' })
      prompts.value = data
      return data
    }
  }

  async function update(id: number, body: PromptIn) {
    return await api<PromptOut>(`prompts/${id}`, {
      method: 'PATCH',
      body,
    })
  }

  async function create(body: PromptIn) {
    return await api<PromptOut>('prompts', {
      method: 'POST',
      body,
    })
  }

  return { create, get, del, update, prompts, loading, error, success }
}
