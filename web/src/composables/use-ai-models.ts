import { useApi } from '@/composables/use-api'
import type { AiModelOut, AiModelIn } from '@/types/openapi'

type UserOpenRouterSettingsOut = {
  apiKey: string | null
  apiHash: string | null
  model: string | null
}

export function useAiModels() {
  const { api, apiUsers, loading, error, success } = useApi()

  async function get(): Promise<AiModelOut[]> {
    return await api<AiModelOut[]>('ai-models', {
      method: 'GET',
    })
  }

  async function save(body: AiModelIn): Promise<AiModelOut> {
    await apiUsers<UserOpenRouterSettingsOut>('auth/openrouter-settings', {
      method: 'POST',
      body: { model: body.id },
    })

    const models = await get()
    const selectedModel = models.find((m) => m.id === body.id)
    if (!selectedModel) {
      throw new Error('Selected model not found')
    }
    return selectedModel
  }

  async function selected(): Promise<AiModelOut> {
    const [models, settings] = await Promise.all([
      get(),
      apiUsers<UserOpenRouterSettingsOut>('auth/openrouter-settings', { method: 'GET' }),
    ])
    const selectedModel = models.find((m) => m.id === settings.model) ?? models[0]
    if (!selectedModel) {
      throw new Error('No AI models available')
    }
    return selectedModel
  }

  return { get, save, selected, loading, error, success }
}
