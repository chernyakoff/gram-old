<template>
  <UModal
    v-model:open="open"
    :dismissible="false"
    :ui="{ content: 'h-screen w-1/3 max-w-none min-w-160 p-6' }">
    <UButton variant="ghost" icon="bx:message-detail" title="Протестировать промпт" />
    <template #content>
      <div class="mb-4 flex items-center justify-between border-b border-default pb-3">
        <h3 class="text-base font-semibold">Тестируем промпт</h3>
        <button
          type="button"
          title="Закрыть"
          class="inline-flex h-8 w-8 items-center justify-center rounded-md text-muted hover:bg-elevated hover:text-default transition-colors"
          @click="open = false">
          <UIcon name="i-lucide-x" class="h-4 w-4" />
        </button>
      </div>
      <UChatPalette>
        <UChatMessages
          :messages="chat.messages.value"
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
              <pre
                v-if="(message as any).role === 'system'"
                class="mb-1 whitespace-pre-wrap rounded-md border border-default bg-elevated px-3 py-2 text-xs font-mono text-muted"
                >{{ getTextFromMessage(message) }}</pre
              >
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
            placeholder="Введите своё сообщение"
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

const open = ref(false)
const { id } = defineProps<{
  id: number
}>()

const { user } = useAuth()
const chat = useChat()

const isTerminal = computed(() =>
  ['complete', 'negative', 'operator'].includes(chat.dialogStatus.value),
)

async function handleSubmit (e: Event) {
  e.preventDefault()
  if (input.value.trim() && id) {
    await chat.sendMessage(id, input.value)
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
