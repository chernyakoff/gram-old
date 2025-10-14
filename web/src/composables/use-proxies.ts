import { ref } from 'vue'

import { useApi } from '@/composables/use-api'

import type { ProxiesBulkCreateIn, ProxyOut, WorkflowOut } from '@/types/openapi'

export function useProxies() {
  const proxies = ref<ProxyOut[]>([])
  const { api, loading, error, success } = useApi()

  async function del(ids: number[]) {
    const query = ids.map((id) => `id=${id}`).join('&')
    return await api(`proxies?${query}`, { method: 'DELETE' })
  }

  async function get(): Promise<ProxyOut[]> {
    const data = await api<ProxyOut[]>('proxies', {
      method: 'GET',
    })
    proxies.value = data
    return data
  }

  async function upload(body: ProxiesBulkCreateIn): Promise<WorkflowOut> {
    return await api<WorkflowOut>('proxies', {
      method: 'POST',
      body,
    })
  }

  return { upload, get, del, proxies, loading, error, success }
}
