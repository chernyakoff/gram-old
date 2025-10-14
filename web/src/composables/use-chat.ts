import { ref } from 'vue'
import type { UIMessage, TextUIPart } from 'ai'
import { getErrorValue, useApi } from './use-api'
import type { ChatOut } from '@/types/openapi'

function toApiMessage(msg: UIMessage): { role: string; text: string } {
  const textParts = msg.parts.filter((p) => p.type === 'text' || p.type === 'reasoning') as Array<{
    text: string
  }>
  return { role: msg.role, text: textParts.map((p) => p.text).join('\n') }
}

function toUIMessage(msg: { role: string; text: string }): UIMessage {
  const part: TextUIPart = { type: 'text', text: msg.text, state: 'done' }
  const id = crypto.randomUUID()
  return {
    id,
    role: msg.role as 'user' | 'assistant' | 'system',
    parts: [part],
  }
}

export function useChat() {
  const { api } = useApi()

  const messages = ref<UIMessage[]>([])
  const status = ref<'ready' | 'submitted' | 'error' | 'submitted'>('ready')
  const error = ref<string | null>(null)

  async function sendMessage(projectId: number, text: string) {
    if (!text) return

    const userMsg = toUIMessage({ role: 'user', text })
    messages.value.push(userMsg)

    status.value = 'submitted'
    error.value = null
    try {
      const data = await api<ChatOut>('chat/', {
        method: 'POST',
        body: {
          projectId: projectId,
          messages: messages.value.map(toApiMessage),
        },
      })

      if (data?.text) {
        messages.value.push(toUIMessage({ role: 'assistant', text: data.text }))
      } else {
        status.value = 'error'
        error.value = 'Сервер вернул пустой ответ'
      }
    } catch (e: unknown) {
      error.value = getErrorValue(e)
    } finally {
      status.value = 'ready'
    }
  }

  async function startWithPrompt(projectId: number) {
    if (!projectId) return

    // сбрасываем чат перед авто-стартом
    messages.value = []
    status.value = 'submitted'
    error.value = null

    try {
      // пустой массив messages — сервер вернёт first_message без запроса к модели
      const data = await api<ChatOut>('chat/', {
        method: 'POST',
        body: { projectId, messages: [] },
      })

      if (data?.text) {
        messages.value.push(toUIMessage({ role: 'assistant', text: data.text }))
      } else {
        error.value = 'Сервер вернул пустой ответ'
      }
    } catch (e: unknown) {
      error.value = getErrorValue(e)
    } finally {
      status.value = 'ready'
    }
  }

  function resetChat() {
    messages.value = []
    status.value = 'ready'
    error.value = null
  }

  return { messages, status, error, sendMessage, startWithPrompt, resetChat }
}
