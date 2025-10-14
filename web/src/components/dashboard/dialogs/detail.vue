<template>
  <UChatPalette>
    <UChatMessages
      :messages="uiMessages"
      :user="{ side: 'right', variant: 'outline' }"
      :assistant="{ side: 'left', variant: 'soft', icon: 'i-lucide-bot' }"
    >
      <template #content="{ message }">
        <p :key="message.id">
          {{ getTextFromMessage(message) }}
        </p>
      </template>
    </UChatMessages>
  </UChatPalette>
</template>

<script setup lang="ts">
import type { DialogMessageOut } from '@/types/openapi'
import type { UIMessage, TextUIPart } from 'ai'
import { computed } from 'vue'
import { getTextFromMessage } from '@nuxt/ui/utils/ai'
function toUIMessage(msg: DialogMessageOut): UIMessage {
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
  }
}
const { messages } = defineProps<{
  messages: DialogMessageOut[]
}>()

const uiMessages = computed(() => messages.map(toUIMessage))
</script>
