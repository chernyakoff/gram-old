import { ref } from 'vue'
import type { UIMessage, TextUIPart } from 'ai'
import { getErrorValue, useApi } from './use-api'
import type { ChatOut, DialogStatus, ToolEvent } from '@/types/openapi'

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

function stripLegacyToolBlock(text: string): string {
  const startMarker = '=== TOOL OUTPUT (test chat) ==='
  const endMarker = '=== END TOOL OUTPUT ==='
  const startIdx = text.indexOf(startMarker)
  if (startIdx === -1) return text
  const endIdx = text.indexOf(endMarker, startIdx)
  if (endIdx === -1) return text

  const after = text.slice(endIdx + endMarker.length)
  return after.trimStart()
}

function isoToHuman(s: string): string | null {
  // Keep tool debug stable: do not apply local timezone conversions.
  // We only reformat the literal ISO strings: YYYY-MM-DD and YYYY-MM-DDTHH:MM...
  const dt = s.match(/^(\d{4})-(\d{2})-(\d{2})[T ](\d{2}):(\d{2})/)
  if (dt) {
    const yy = dt[1].slice(2, 4)
    return `${dt[3]}.${dt[2]}.${yy} ${dt[4]}:${dt[5]}`
  }
  const d = s.match(/^(\d{4})-(\d{2})-(\d{2})$/)
  if (d) {
    const yy = d[1].slice(2, 4)
    return `${d[3]}.${d[2]}.${yy}`
  }
  return null
}

function slotKeyToHuman(s: string): string | null {
  const m = s.match(/^(\d+)__(.+)__(.+)$/)
  if (!m) return null
  const a = isoToHuman(m[2]) ?? m[2]
  const b = isoToHuman(m[3]) ?? m[3]
  return `${m[1]}__${a}__${b}`
}

function humanizeDebugValue(v: unknown): unknown {
  if (Array.isArray(v)) return v.map(humanizeDebugValue)
  if (v && typeof v === 'object') {
    const out: Record<string, unknown> = {}
    for (const [k, val] of Object.entries(v as Record<string, unknown>)) {
      out[k] = humanizeDebugValue(val)
    }
    return out
  }
  if (typeof v === 'string') {
    return slotKeyToHuman(v) ?? isoToHuman(v) ?? v
  }
  return v
}

function toolEventToText(ev: ToolEvent): string {
  const args = JSON.stringify(humanizeDebugValue(ev.arguments ?? {}), null, 2)
  const result = JSON.stringify(humanizeDebugValue(ev.result ?? null), null, 2)
  return `TOOL: ${ev.tool}\nargs: ${args}\nresult:\n${result}`
}

function warningToText(w: string): string {
  return `WARNING: ${w}`
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
        if (data.warnings?.length) {
          for (const w of data.warnings) {
            messages.value.push(
              toUIMessage({ role: 'system', text: warningToText(w) }, dialogStatus.value),
            )
          }
        }
        if (data.toolEvents?.length) {
          for (const ev of data.toolEvents) {
            messages.value.push(
              toUIMessage({ role: 'system', text: toolEventToText(ev) }, dialogStatus.value),
            )
          }
        }
        messages.value.push(
          toUIMessage(
            { role: 'assistant', text: stripLegacyToolBlock(data.text) },
            dialogStatus.value,
          ),
        )
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
        if (data.warnings?.length) {
          for (const w of data.warnings) {
            messages.value.push(
              toUIMessage({ role: 'system', text: warningToText(w) }, dialogStatus.value),
            )
          }
        }
        if (data.toolEvents?.length) {
          for (const ev of data.toolEvents) {
            messages.value.push(
              toUIMessage({ role: 'system', text: toolEventToText(ev) }, dialogStatus.value),
            )
          }
        }
        messages.value.push(
          toUIMessage(
            { role: 'assistant', text: stripLegacyToolBlock(data.text) },
            dialogStatus.value,
          ),
        )
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
