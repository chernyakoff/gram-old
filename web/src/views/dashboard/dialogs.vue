<template>
  <UDashboardPanel id="dialogs" :default-size="25" :min-size="20" :max-size="30" resizable>
    <UDashboardNavbar>
      <template #leading>
        <UDashboardSidebarCollapse />
      </template>
      <template #trailing>
        <UBadge :label="filteredDialogs.length" variant="subtle" />
      </template>
      <template #right>
        <USelect
          v-model="statusFilter"
          :items="statuses"
          :ui="{
            trailingIcon: 'group-data-[state=open]:rotate-180 transition-transform duration-200',
          }"
          placeholder="Filter status"
          class="min-w-28"
        />
        <DialogFilterModal @apply="handleFilterApply" @reset="handleFilterReset" />
      </template>
    </UDashboardNavbar>
    <DialogMenu v-model="selectedDialog" :dialogs="filteredDialogs" :statuses="statuses" />
  </UDashboardPanel>

  <div v-if="selectedDialog" class="flex flex-col lg:flex-row gap-4 w-full">
    <div class="flex flex-col w-full">
      <!-- Важная обертка -->
      <DialogInfo :dialog="selectedDialog" />
      <DialogDetail
        :messages="messages"
        :dialogId="selectedDialog.id"
        @messages-updated="handleMessagesUpdated"
        class="flex-1 w-full"
      />
    </div>
  </div>

  <div v-else class="hidden lg:flex flex-1 items-center justify-center">
    <UIcon name="i-lucide-logs" class="size-32 text-dimmed" />
  </div>
</template>
<script setup lang="ts">
import DialogMenu from '@/components/dashboard/dialogs/menu.vue'
import DialogDetail from '@/components/dashboard/dialogs/detail.vue'
import DialogInfo from '@/components/dashboard/dialogs/info.vue'
import DialogFilterModal from '@/components/dashboard/dialogs/filter-modal.vue'
import { useTitle } from '@vueuse/core'
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useDialogs } from '@/composables/use-dialogs'
import type { DialogIn, DialogMessageOut, DialogOut } from '@/types/openapi'
import { statuses } from '@/utils/status'

const title = 'Диалоги'
useTitle(title)

const { dialogs, get, list } = useDialogs()

const payload = reactive<DialogIn>({
  accountId: null,
  projectId: null,
  mailingId: null,
  recipientId: null,
})

onMounted(() => list(payload))

const statusFilter = ref('all')

const selectedDialog = ref<DialogOut | null>()
const messages = ref<DialogMessageOut[]>([])

watch(selectedDialog, async (dialog) => {
  if (dialog) {
    messages.value = await get(dialog.id)
  } else {
    messages.value = []
  }
})

function handleMessagesUpdated(updatedMessages: DialogMessageOut[]) {
  messages.value = updatedMessages
}

function handleFilterApply(filterPayload: DialogIn) {
  // Обновляем реактивный payload
  payload.accountId = filterPayload.accountId
  payload.projectId = filterPayload.projectId
  payload.mailingId = filterPayload.mailingId
  payload.recipientId = filterPayload.recipientId

  // Загружаем диалоги с новыми фильтрами
  list(payload)
}

function handleFilterReset() {
  // Сбрасываем фильтры
  payload.accountId = null
  payload.projectId = null
  payload.mailingId = null
  payload.recipientId = null

  // Загружаем все диалоги
  list(payload)
}

const filteredDialogs = computed(() => {
  if (statusFilter.value === 'all') return dialogs.value
  return dialogs.value.filter((d) => d.status === statusFilter.value)
})
</script>
