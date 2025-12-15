<template>
  <UChatPalette>
    <UChatMessages
      class="min-w-[600px] max-w-4xl mx-auto"
      :messages="uiMessages"
      :user="{ side: 'right', variant: 'outline' }"
      :assistant="{ side: 'left', variant: 'soft', icon: 'i-lucide-bot' }"
    >
      <template #content="{ message }">
        <!-- SYSTEM -->
        <div v-if="message.role === 'system'" class="flex justify-center w-full">
          <div class="relative bg-gray-100 dark:bg-gray-800 rounded-lg px-4 py-2 max-w-md">
            <div class="flex items-center gap-2 text-gray-600 dark:text-gray-400">
              <UIcon name="i-lucide-info" class="size-4" />
              <p class="text-sm whitespace-pre-line">
                {{ getTextFromMessage(message) }}
              </p>
            </div>

            <small class="absolute bottom-1 right-2 flex items-center gap-1 text-gray-500 text-xs">
              {{ formatTime(message) }}

              <template v-if="shouldShowChecks(message)">
                <UIcon
                  v-if="(message as UIMessageWithTime).ack"
                  name="i-lucide-check-check"
                  class="size-4 text-blue-500"
                />
                <UIcon v-else name="i-lucide-check" class="size-4 text-gray-400" />
              </template>
            </small>
          </div>
        </div>

        <!-- USER + ASSISTANT -->
        <div v-else class="relative min-w-20 p-2">
          <p class="mb-4 whitespace-pre-line">
            {{ getTextFromMessage(message) }}
          </p>

          <small
            class="absolute bottom-1 right-2 flex items-center gap-1 text-gray-500 text-xs text-nowrap"
          >
            {{ formatTime(message) }}

            <template v-if="shouldShowChecks(message)">
              <UIcon
                v-if="(message as UIMessageWithTime).ack"
                name="i-lucide-check-check"
                class="size-4 text-blue-500"
              />
              <UIcon v-else name="i-lucide-check" class="size-4 text-gray-400" />
            </template>
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
        :disabled="loading"
        @submit="handleSubmit"
      >
        <UChatPromptSubmit :loading="loading" />
      </UChatPrompt>
    </template>
  </UChatPalette>
</template>

<script setup lang="ts">
import type { DialogMessageOut } from '@/types/openapi'
import type { UIMessage, TextUIPart } from 'ai'
import { computed, ref } from 'vue'
import { getTextFromMessage } from '@nuxt/ui/utils/ai'
import { useDialogs } from '@/composables/use-dialogs'

interface UIMessageWithTime extends UIMessage {
  createdAt?: string
  ack?: boolean
}

const props = defineProps<{
  messages: DialogMessageOut[]
  dialogId: number
}>()

const emit = defineEmits<{
  'messages-updated': [messages: DialogMessageOut[]]
}>()

const { add, loading } = useDialogs()
const input = ref('')

function toUIMessage(msg: DialogMessageOut): UIMessageWithTime {
  const part: TextUIPart = { type: 'text', text: msg.text, state: 'done' }

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
    ack: msg.ack,
  }
}

/**
 * Показываем галочки только для system и assistant,
 * и только если ack вообще есть
 */
function shouldShowChecks(message: UIMessage): boolean {
  const msg = message as UIMessageWithTime
  return (message.role === 'system' || message.role === 'assistant') && msg.ack !== undefined
}

function formatTime(message: UIMessage): string {
  const msg = message as UIMessageWithTime
  if (!msg.createdAt) return ''

  return new Date(msg.createdAt).toLocaleString('ru-RU', {
    day: '2-digit',
    month: '2-digit',
    year: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  })
}
async function handleSubmit() {
  if (!input.value.trim() || loading.value) return

  const messageText = input.value.trim()
  input.value = ''

  try {
    const updatedMessages = await add({
      dialogId: props.dialogId,
      message: messageText,
    })

    emit('messages-updated', updatedMessages)
  } catch (error) {
    console.error('Ошибка отправки сообщения:', error)
    input.value = messageText
  }
}

const uiMessages = computed<UIMessageWithTime[]>(() => props.messages.map(toUIMessage))
</script>
