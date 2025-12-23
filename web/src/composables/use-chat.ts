import { ref } from 'vue'
import type { UIMessage, TextUIPart } from 'ai'
import { getErrorValue, useApi } from './use-api'
import type { ChatOut, DialogStatus } from '@/types/openapi'

export interface UIMessageWithStatus extends UIMessage {
  status: DialogStatus
}

function toApiMessage(msg: UIMessageWithStatus): { role: string; text: string } {
  const textParts = msg.parts.filter((p) => p.type === 'text' || p.type === 'reasoning') as Array<{
    text: string
  }>
  return { role: msg.role, text: textParts.map((p) => p.text).join('\n') }
}

function toUIMessage(
  msg: { role: string; text: string },
  status: DialogStatus,
): UIMessageWithStatus {
  const part: TextUIPart = { type: 'text', text: msg.text, state: 'done' }
  const id = crypto.randomUUID()
  return {
    id,
    role: msg.role as 'user' | 'assistant' | 'system',
    parts: [part],
    status,
  }
}

export function useChat() {
  const { api } = useApi()

  const messages = ref<UIMessageWithStatus[]>([])
  const status = ref<'ready' | 'submitted' | 'error' | 'submitted'>('ready')
  const error = ref<string | null>(null)
  const dialogStatus = ref<DialogStatus>('init')

  async function sendMessage(projectId: number, text: string) {
    if (!text) return

    const userMsg = toUIMessage({ role: 'user', text }, dialogStatus.value)
    messages.value.push(userMsg)

    status.value = 'submitted'
    error.value = null
    try {
      const data = await api<ChatOut>('chat/', {
        method: 'POST',
        body: {
          projectId: projectId,
          messages: messages.value.map(toApiMessage),
          status: dialogStatus.value,
        },
      })
      dialogStatus.value = data.status

      if (data?.text) {
        messages.value.push(toUIMessage({ role: 'assistant', text: data.text }, dialogStatus.value))
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
        body: { projectId, messages: [], status: dialogStatus.value },
      })
      dialogStatus.value = data.status
      if (data?.text) {
        messages.value.push(toUIMessage({ role: 'assistant', text: data.text }, dialogStatus.value))
      } else {
        error.value = 'Сервер вернул пустой ответ'
      }
    } catch (e: unknown) {
      error.value = getErrorValue(e)
    } finally {
      status.value = 'ready'
    }
  }

  function reset() {
    messages.value = []
    status.value = 'ready'
    error.value = null
    dialogStatus.value = 'init'
  }

  return { messages, status, error, dialogStatus, sendMessage, startWithPrompt, reset }
}
