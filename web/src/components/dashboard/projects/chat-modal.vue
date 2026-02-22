<template>
  <UModal
    v-model:open="open"
    :dismissible="false"
    :ui="{ content: 'h-screen w-1/3 max-w-none min-w-160 p-6' }">
    <UButton variant="ghost" icon="bx:message-detail" title="Протестировать промпт" />
    <template #content>
      <div class="mb-4 flex items-center justify-between border-b border-default pb-3">
        <h3 class="text-base font-semibold">Тестируем промпт</h3>
        <div class="flex items-center gap-3">
          <div class="flex items-center gap-2 select-none">
            <span
              class="text-xs text-muted"
              title="Показывать системные сообщения (warnings/tools)"
            >
              Отладка
            </span>
            <USwitch v-model="debug" class="scale-75 origin-right" />
          </div>
          <button
            type="button"
            title="Закрыть"
            class="inline-flex h-8 w-8 items-center justify-center rounded-md text-muted hover:bg-elevated hover:text-default transition-colors"
            @click="open = false">
            <UIcon name="i-lucide-x" class="h-4 w-4" />
          </button>
        </div>
      </div>
      <UChatPalette>
        <UChatMessages
          :messages="visibleMessages"
          :status="chat.status.value"
          :user="{
            side: 'right',
            variant: 'outline',
            avatar: { src: user?.photoUrl as string, size: 'md' },
          }"
          :assistant="{
            side: 'left',
            variant: 'soft',
            icon: 'i-lucide-bot',
          }">
          <template #content="{ message }">
            <div class="min-w-20 p-2">
              <template v-if="(message as any).role === 'system'">
                <details
                  v-if="isToolDebugMessage(message)"
                  class="tool-debug mb-1 rounded-md border border-default bg-elevated px-3 py-2 text-xs font-mono text-muted"
                >
                  <summary class="flex items-center gap-2 cursor-pointer select-none">
                    <span class="tool-debug__pm tool-debug__pm--closed">+</span>
                    <span class="tool-debug__pm tool-debug__pm--open">-</span>
                    <span class="whitespace-pre-wrap">{{ toolDebugSummary(message) }}</span>
                  </summary>
                  <div class="mt-2">
                    <div class="whitespace-pre-wrap">{{ toolDebugArgs(message) }}</div>
                    <div class="mt-2">result:</div>
                    <pre class="mt-1 whitespace-pre-wrap">{{ toolDebugResult(message) }}</pre>
                  </div>
                </details>
                <pre
                  v-else
                  class="mb-1 whitespace-pre-wrap rounded-md border border-default bg-elevated px-3 py-2 text-xs font-mono text-muted"
                >{{ getTextFromMessage(message) }}</pre>
              </template>
              <p v-else class="mb-4 whitespace-pre-line">{{ getTextFromMessage(message) }}</p>
              <small
                v-if="(message as any).role !== 'system'"
                class="absolute bottom-1 right-2 text-gray-500 text-xs text-nowrap">
                <UBadge
                  :style="{
                    backgroundColor: statusColor[(message as UIMessageWithStatus).status],
                  }">
                  {{ (message as UIMessageWithStatus).status }}
                </UBadge>
              </small>
            </div>
          </template>
        </UChatMessages>
        <template #prompt>
          <UChatPrompt
            ref="promptRef"
            placeholder="Введите сообщение (команда /fu для follow-up)"
            v-model="input"
            icon="i-lucide-search"
            variant="naked"
            :error="chat.error.value ? new Error(chat.error.value) : undefined"
            :disabled="chat.status.value === 'submitted' || isTerminal"
            @submit="handleSubmit">
            <UChatPromptSubmit :status="chat.status.value" />
          </UChatPrompt>
        </template>
      </UChatPalette>
    </template>
  </UModal>
</template>
<script setup lang="ts">
import { computed, nextTick, ref, watch } from 'vue'
import type { ComponentPublicInstance } from 'vue'

import { getTextFromMessage } from '@nuxt/ui/utils/ai'
import { useChat, type UIMessageWithStatus } from '@/composables/use-chat'
import { useAuth } from '@/composables/use-auth'
import { statusColor } from '@/utils/status'
const input = ref('')
const promptRef = ref<ComponentPublicInstance | null>(null)
const debug = ref(false)

const open = ref(false)
const { id } = defineProps<{
  id: number
}>()

const { user } = useAuth()
const chat = useChat()

const isTerminal = computed(() =>
  ['complete', 'negative', 'operator'].includes(chat.dialogStatus.value),
)

const visibleMessages = computed(() =>
  debug.value ? chat.messages.value : chat.messages.value.filter((m) => m.role !== 'system'),
)

type ToolDebugParts = { tool: string; args: string; result: string } | null

function parseToolDebugText(text: string): ToolDebugParts {
  if (!text.startsWith('TOOL:')) return null
  const toolMatch = text.match(/^TOOL:\s*(.+)\s*$/m)
  const tool = toolMatch?.[1]?.trim() || 'unknown'

  const argsIdx = text.indexOf('\nargs:')
  const resIdx = text.indexOf('\nresult:')
  if (argsIdx === -1 || resIdx === -1 || resIdx < argsIdx) return null

  const args = text.slice(argsIdx + '\nargs:'.length, resIdx).trim()
  const result = text.slice(resIdx + '\nresult:'.length).trim()
  return { tool, args, result }
}

function isToolDebugMessage(message: any): boolean {
  const text = String(getTextFromMessage(message) ?? '')
  return parseToolDebugText(text) !== null
}

function toolDebugSummary(message: any): string {
  const text = String(getTextFromMessage(message) ?? '')
  const p = parseToolDebugText(text)
  if (!p) return text
  // Keep summary single-line-ish.
  const argsOneLine = p.args.replace(/\s+/g, ' ').slice(0, 120)
  const suffix = p.args.length > 120 ? '…' : ''
  return `TOOL: ${p.tool} | args: ${argsOneLine}${suffix} | result:`
}

function toolDebugArgs(message: any): string {
  const text = String(getTextFromMessage(message) ?? '')
  const p = parseToolDebugText(text)
  if (!p) return ''
  return `args: ${p.args}`
}

function toolDebugResult(message: any): string {
  const text = String(getTextFromMessage(message) ?? '')
  const p = parseToolDebugText(text)
  if (!p) return text
  return p.result
}

async function handleSubmit (e: Event) {
  e.preventDefault()
  const text = input.value.trim()
  if (text && id) {
    if (text.toLowerCase() === '/fu') {
      await chat.sendFollowUp(id)
    } else {
      await chat.sendMessage(id, text)
    }
    input.value = ''

    await nextTick()
    const root = promptRef.value?.$el as HTMLElement | undefined
    const inputEl = root?.querySelector('input,textarea') as
      | HTMLInputElement
      | HTMLTextAreaElement
      | null
    inputEl?.focus()
  }
}

// Авто-старт при открытии модалки
watch(
  [open, () => id],
  async ([isOpen, id]) => {
    if (isOpen && id) {
      chat.reset()
      await chat.startWithPrompt(id)
      await nextTick()
      const root = promptRef.value?.$el as HTMLElement | undefined
      const inputEl = root?.querySelector('input,textarea') as
        | HTMLInputElement
        | HTMLTextAreaElement
        | null
      inputEl?.focus()
    }
  },
  { immediate: true },
)
</script>

<style scoped>
.tool-debug__pm--open {
  display: none;
}
.tool-debug[open] .tool-debug__pm--open {
  display: inline;
}
.tool-debug[open] .tool-debug__pm--closed {
  display: none;
}
</style>
