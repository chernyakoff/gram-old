import { useApi } from '@/composables/use-api'
import type { MobProxyCreateIn, MobProxyOut, MobProxyUpdateIn } from '@/types/openapi'

export function useMobProxy() {
  const { api, loading, error, success } = useApi()

  async function get(): Promise<MobProxyOut | null> {
    return await api<MobProxyOut | null>('mob-proxies', { method: 'GET' })
  }

  async function create(body: MobProxyCreateIn): Promise<MobProxyOut> {
    return await api<MobProxyOut>('mob-proxies', { method: 'POST', body })
  }

  async function update(body: MobProxyUpdateIn): Promise<MobProxyOut> {
    return await api<MobProxyOut>('mob-proxies', { method: 'PATCH', body })
  }

  async function del(): Promise<{ deleted: number }> {
    return await api<{ deleted: number }>('mob-proxies', { method: 'DELETE' })
  }

  return { get, create, update, del, loading, error, success }
}
