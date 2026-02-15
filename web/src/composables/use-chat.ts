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
    const yyyy = dt[1]
    const mm = dt[2]
    const dd = dt[3]
    const hh = dt[4]
    const mi = dt[5]
    if (!yyyy || !mm || !dd || !hh || !mi) return null
    const yy = yyyy.slice(2, 4)
    return `${dd}.${mm}.${yy} ${hh}:${mi}`
  }
  const d = s.match(/^(\d{4})-(\d{2})-(\d{2})$/)
  if (d) {
    const yyyy = d[1]
    const mm = d[2]
    const dd = d[3]
    if (!yyyy || !mm || !dd) return null
    const yy = yyyy.slice(2, 4)
    return `${dd}.${mm}.${yy}`
  }
  return null
}

function slotKeyToHuman(s: string): string | null {
  const m = s.match(/^(\d+)__(.+)__(.+)$/)
  if (!m) return null
  const id = m[1]
  const start = m[2]
  const end = m[3]
  if (!id || !start || !end) return null
  const a = isoToHuman(start) ?? start
  const b = isoToHuman(end) ?? end
  return `${id}__${a}__${b}`
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

  async function maybeInjectTestReminder(projectId: number) {
    // Only used by the prompt test UI: after a terminal status, ask the backend
    // for the next reminder (without calling the LLM) and reopen the dialog.
    if (dialogStatus.value !== 'complete') return

    try {
      const data = await api<ChatOut>('chat/test-reminders', {
        method: 'POST',
        body: { projectId },
      })

      if (data?.text && data.text.trim()) {
        dialogStatus.value = data.status
        messages.value.push(toUIMessage({ role: 'assistant', text: data.text }, dialogStatus.value))
      } else {
        // Keep the terminal status as-is.
        dialogStatus.value = data.status
      }
    } catch {
      // Ignore reminder failures in the test UI.
    }
  }

  function toApiMessages() {
    // Do not send local debug/system messages back to the server, otherwise the LLM may
    // "learn" a human-formatted slotKey and reuse it in tool calls, breaking booking.
    return messages.value
      .filter((m) => m.role !== 'system')
      .map(toApiMessage)
  }

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
          messages: toApiMessages(),
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

        await maybeInjectTestReminder(projectId)
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
