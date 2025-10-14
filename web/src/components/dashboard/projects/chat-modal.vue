<template>
  <UModal v-model:open="open" :ui="{ content: 'h-screen w-1/3 max-w-none min-w-160 p-6' }">
    <UButton variant="ghost" icon="lucide:message-square-more" title="Протестировать промпт" />
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
            <p :key="message.id">
              {{ getTextFromMessage(message) }}
            </p>
          </template>
        </UChatMessages>

        <template #prompt>
          <UChatPrompt
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
import { ref, watch } from 'vue'
import { getTextFromMessage } from '@nuxt/ui/utils/ai'
import { useChat } from '@/composables/use-chat'
import { useAuth } from '@/composables/use-auth'

const input = ref('')

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
  }
}

// Авто-старт при открытии модалки
watch(
  [open, () => id],
  async ([isOpen, id]) => {
    if (isOpen && id) {
      await chat.startWithPrompt(id)
    }
  },
  { immediate: true },
)
</script>
