<template>
  <UChatPalette>
    <UChatMessages
      class="min-w-[600px] max-w-4xl mx-auto"
      :messages="uiMessages"
      :user="{ side: 'right', variant: 'outline' }"
      :assistant="{ side: 'left', variant: 'soft', icon: 'i-lucide-bot' }"
    >
      <template #content="{ message }">
        <div class="min-w-20 p-2">
          <p class="mb-4">{{ getTextFromMessage(message) }}</p>

          <small class="absolute bottom-1 right-2 text-gray-500 text-xs text-nowrap">
            {{
              (message as UIMessageWithTime).createdAt
                ? new Date((message as UIMessageWithTime).createdAt!).toLocaleTimeString([], {
                    hour: '2-digit',
                    minute: '2-digit',
                  })
                : ''
            }}
          </small>
        </div>
      </template>
    </UChatMessages>
    <template #prompt>
      <UChatPrompt
        class="min-w-[600px] max-w-4xl mx-auto"
        placeholder="Введите своё сообщение"
        v-model="input"
        icon="i-lucide-search"
        variant="naked"
        @submit="handleSubmit"
      >
        <UChatPromptSubmit />
      </UChatPrompt>
    </template>
  </UChatPalette>
</template>

<script setup lang="ts">
import type { DialogMessageOut } from '@/types/openapi'
import type { UIMessage, TextUIPart } from 'ai'
import { computed, ref } from 'vue'
import { getTextFromMessage } from '@nuxt/ui/utils/ai'
interface UIMessageWithTime extends UIMessage {
  createdAt?: string
}

const input = ref('')

function toUIMessage(msg: DialogMessageOut): UIMessageWithTime {
  const part: TextUIPart = { type: 'text', text: msg.text, state: 'done' }

  // Маппинг ролей
  let role: 'user' | 'assistant' | 'system'
  switch (msg.sender) {
    case 'account':
      role = 'assistant'
      break
    case 'recipient':
      role = 'user'
      break
    case 'system':
    default:
      role = 'system'
      break
  }
  return {
    id: crypto.randomUUID(),
    role,
    parts: [part],
    createdAt: msg.createdAt,
  }
}

function handleSubmit() {
  console.log('asas')
}

const { messages } = defineProps<{
  messages: DialogMessageOut[]
}>()

const uiMessages = computed<UIMessageWithTime[]>(() => messages.map(toUIMessage))
</script>
