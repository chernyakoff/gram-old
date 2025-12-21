import { useApi } from '@/composables/use-api'
import type { AiModelOut, AiModelIn } from '@/types/openapi'

export function useAiModels() {
  const { api, loading, error, success } = useApi()

  async function get(): Promise<AiModelOut[]> {
    return await api<AiModelOut[]>('ai-models', {
      method: 'GET',
    })
  }

  async function save(body: AiModelIn): Promise<AiModelOut> {
    return await api<AiModelOut>('ai-models', {
      method: 'POST',
      body,
    })
  }

  async function selected(): Promise<AiModelOut> {
    return await api<AiModelOut>('ai-models/selected', {
      method: 'GET',
    })
  }

  return { get, save, selected, loading, error, success }
}
