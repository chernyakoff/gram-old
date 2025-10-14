<template>
  <UDashboardPanel id="prompts">
    <template #header>
      <UDashboardNavbar :title="title" :ui="{ right: 'gap-3' }">
        <template #leading>
          <UDashboardSidebarCollapse />
        </template>
        <template #right>
          <UButton label="Добавить" icon="i-lucide-plus" @click="openDrawer()" />
        </template>
      </UDashboardNavbar>
    </template>
    <template #body>
      <div class="flex flex-wrap items-center justify-end gap-1.5">
        <DeleteModal :selected-ids="selectedIds" @close="refresh" />
      </div>
      <UTable
        ref="table"
        v-model:column-filters="columnFilters"
        v-model:column-visibility="columnVisibility"
        class="shrink-0"
        :data="prompts ?? []"
        :columns="columns"
        :loading="loading"
        :ui="{
          base: 'table-fixed border-separate border-spacing-0',
          thead: '[&>tr]:bg-elevated/50 [&>tr]:after:content-none',
          tbody: '[&>tr]:last:[&>td]:border-b-0',
          th: 'py-2 first:rounded-l-lg last:rounded-r-lg border-y border-default first:border-l last:border-r',
          td: 'border-b border-default',
        }"
      >
        <template #name-cell="{ row }">
          <UButton
            class="p-0"
            variant="link"
            :label="row.getValue('name')"
            @click="openDrawer(row.original.id)"
          />
        </template>
        <template #test-cell="{ row }">
          <UButton
            variant="ghost"
            icon="lucide:message-square-more"
            @click="openChat(row.original.id)"
          />
        </template>
      </UTable>
    </template>
  </UDashboardPanel>
  <Drawer v-model:open="drawerOpen" :promptId="selectedPromptId" @closed="refresh" />
  <ChatModal v-model:open="chatOpen" :promptId="selectedPromptId" />
</template>
<script setup lang="ts">
import type { TableColumn } from '@nuxt/ui'
import { ref, onMounted } from 'vue'
import { useTitle, useDateFormat } from '@vueuse/core'
import Drawer from '@/components/dashboard/prompts/drawer.vue'
import DeleteModal from '@/components/dashboard/prompts/delete-modal.vue'
import ChatModal from '@/components/dashboard/prompts/chat-modal.vue'

import { useTableSelection } from '@/composables/table/use-selection'
import { usePrompts } from '@/composables/use-prompts'
import type { PromptOut } from '@/types/openapi'

const { prompts, get, loading } = usePrompts()

const title = 'Промпты'
useTitle(title)

onMounted(() => get())

// - drawer

const drawerOpen = ref(false)
const chatOpen = ref(false)
const selectedPromptId = ref<number | undefined>()

function openDrawer(id?: number) {
  selectedPromptId.value = id
  drawerOpen.value = true
}

function openChat(id?: number) {
  selectedPromptId.value = id
  chatOpen.value = true
}

//- table
const columnFilters = ref([{ id: 'name', value: '' }])
const columnVisibility = ref()

const { tableApi, selectedIds, selectionColumn } = useTableSelection<PromptOut>('table')

const refresh = () => {
  tableApi.value?.setRowSelection({})
  get()
}

const columns: TableColumn<PromptOut>[] = [
  selectionColumn(),
  {
    accessorKey: 'id',
    header: 'ID',
  },
  {
    accessorKey: 'project',
    header: 'Проект',
    cell: ({ row }) => {
      return row.original.project.name
    },
  },
  {
    accessorKey: 'name',
    header: 'Название',
  },
  {
    accessorKey: 'test',
    header: 'Тест',
  },
  {
    accessorKey: 'createdAt',
    header: 'Создан',
    cell: ({ row }) => useDateFormat(row.original.createdAt, 'DD.MM.YY').value,
  },
]
</script>
