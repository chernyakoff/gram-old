<template>
  <UDashboardPanel id="dialogs" :default-size="25" :min-size="20" :max-size="30" resizable>
    <UDashboardNavbar :title="title">
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
      </template>
    </UDashboardNavbar>
    <Menu v-model="selectedDialog" :dialogs="filteredDialogs" :statuses="statuses" />
  </UDashboardPanel>
  <Detail v-if="selectedDialog" :messages="messages" />
  <div v-else class="hidden lg:flex flex-1 items-center justify-center">
    <UIcon name="i-lucide-logs" class="size-32 text-dimmed" />
  </div>
</template>
<script setup lang="ts">
import Menu from '@/components/dashboard/dialogs/menu.vue'
import Detail from '@/components/dashboard/dialogs/detail.vue'

import { useTitle } from '@vueuse/core'
import { computed, onMounted, ref, watch } from 'vue'
import { useDialogs } from '@/composables/use-dialogs'
import type { DialogMessageOut, DialogOut } from '@/types/openapi'
const title = 'Диалоги'
useTitle(title)

const { dialogs, get } = useDialogs()

onMounted(() => get())

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

const filteredDialogs = computed(() => {
  if (statusFilter.value === 'all') return dialogs.value
  return dialogs.value.filter((d) => d.status === statusFilter.value)
})

const statuses = [
  { label: 'все', value: 'all' },
  { label: 'начат.', value: 'init' },
  { label: 'интерес', value: 'engage' },
  { label: 'заявка', value: 'offer' },
  { label: 'закрыт', value: 'close' },
]
</script>
