<template>
  <UModal v-model:open="open" :title="title" :description="description">
    <template #body>
      <UChatPalette>
        <UChatMessages
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

                <small
                  class="absolute bottom-1 right-2 flex items-center gap-1 text-gray-500 text-xs"
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
      </UChatPalette>
    </template>
  </UModal>
</template>
<script setup lang="ts">
import type { DialogMessageOut, MeetingOut } from '@/types/openapi'
import { computed, ref, watchEffect } from 'vue'
import { useDateFormat } from '@vueuse/core'
import { useDialogs } from '@/composables/use-dialogs'
import type { UIMessage, TextUIPart } from 'ai'
import { getTextFromMessage } from '@nuxt/ui/utils/ai'

const open = defineModel<boolean>({ default: false })
const messages = ref<DialogMessageOut[]>([])

interface UIMessageWithTime extends UIMessage {
  createdAt?: string
  ack?: boolean
}
const { get } = useDialogs()

const { meeting } = defineProps<{
  meeting: MeetingOut
}>()
const title = computed(() => `@${meeting.username}`)
const description = computed(() => formatMeetingTime(meeting.startAt, meeting.endAt))

const uiMessages = computed<UIMessageWithTime[]>(() => messages.value.map(toUIMessage))

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

watchEffect(async () => {
  if (open.value) {
    console.log('модалка открыта')
    messages.value = await get(meeting.dialogId)
  }
})

function formatMeetingTime(start: string, end: string) {
  const s = useDateFormat(start, 'HH:mm').value
  const e = useDateFormat(end, 'HH:mm').value
  return `${s}–${e}`
}
</script>
