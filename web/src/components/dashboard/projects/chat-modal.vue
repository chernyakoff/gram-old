<template>
  <UModal v-model:open="open" :ui="{ content: 'h-screen w-1/3 max-w-none min-w-160 p-6' }">
    <UButton variant="ghost" icon="bx:message-detail" title="Протестировать промпт" />
    <template #content>
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
          }"
        >
          <template #content="{ message }">
            <div class="min-w-20 p-2">
              <p class="mb-4">{{ getTextFromMessage(message) }}</p>
              <small class="absolute bottom-1 right-2 text-gray-500 text-xs text-nowrap">
                <UBadge
                  :style="{
                    backgroundColor: statusColorMap[(message as UIMessageWithStatus).status],
                  }"
                >
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
            :disabled="chat.status.value === 'submitted'"
            @submit="handleSubmit"
          >
            <UChatPromptSubmit :status="chat.status.value" />
          </UChatPrompt>
        </template>
      </UChatPalette>
    </template>
  </UModal>
</template>

<script setup lang="ts">
import { nextTick, ref, watch } from 'vue'
import type { ComponentPublicInstance } from 'vue'

import { getTextFromMessage } from '@nuxt/ui/utils/ai'
import { useChat, type UIMessageWithStatus } from '@/composables/use-chat'
import { useAuth } from '@/composables/use-auth'

const input = ref('')
const promptRef = ref<ComponentPublicInstance | null>(null)

const statusColorMap = {
  init: '#006a6c',
  engage: '#8e90ff',
  offer: '#ffab00',
  closing: '#71dd37',
  complete: '#fff',
} as const

const open = ref(false)
const { id } = defineProps<{
  id: number
}>()

const { user } = useAuth()
const chat = useChat()

async function handleSubmit(e: Event) {
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
