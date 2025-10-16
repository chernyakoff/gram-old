<template>
  <UDashboardPanel id="mailings">
    <template #header>
      <UDashboardNavbar :title="title" :ui="{ right: 'gap-3' }">
        <template #leading>
          <UDashboardSidebarCollapse />
        </template>
        <template #right>
          <AddMailingModal @close="refresh" />
        </template>
      </UDashboardNavbar>
    </template>
    <template #body>
      <div class="min-w-[600px] max-w-4xl mx-auto">
        <UTable
          ref="table"
          v-model:column-filters="columnFilters"
          v-model:column-visibility="columnVisibility"
          class="shrink-0 w-full"
          :data="mailings ?? []"
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
          <template #status-cell="{ row }">
            <UBadge
              class="opacity-80"
              :label="getStatusInfo(row.original.status).label"
              :color="getStatusInfo(row.original.status).color"
            />
          </template>
          <template #actions-cell="{ row }">
            <div class="flex items-center justify-end w-32">
              <DeleteMailingModal :id="row.original.id" @close="refresh" />
            </div>
          </template>
        </UTable>
      </div>
    </template>
  </UDashboardPanel>
</template>
<script setup lang="ts">
import { useTitle } from '@vueuse/core'
import AddMailingModal from '@/components/dashboard/mailings/add-modal.vue'
import DeleteMailingModal from '@/components/dashboard/mailings/delete-modal.vue'
import { useMailings } from '@/composables/use-mailings'
import { onMounted, ref } from 'vue'
import type { MailingOut } from '@/types/openapi'
import type { TableColumn } from '@nuxt/ui'
const title = 'Рассылки'
useTitle(title)

const { mailings, get, loading } = useMailings()

onMounted(() => get())

const columnFilters = ref([{ id: 'name', value: '' }])
const columnVisibility = ref()

const refresh = () => {
  get()
}

const statusMap = {
  draft: { label: 'Создана', color: 'warning' },
  running: { label: 'Запущена', color: 'primary' },
  finished: { label: 'Завершёна', color: 'success' },
  cancelled: { label: 'Отменёна', color: 'error' },
} as const

type Status = keyof typeof statusMap

function getStatusInfo(status: string) {
  return statusMap[status as Status] ?? { label: 'Неизвестно', color: 'default' }
}

const columns: TableColumn<MailingOut>[] = [
  {
    accessorKey: 'name',
    header: 'Название',
  },
  {
    accessorKey: 'project',
    header: 'Проект',
    cell: ({ row }) => {
      return row.original.project.name
    },
  },
  {
    accessorKey: 'counts',
    header: 'Отправлено/Ошибка/Всего',
    cell: ({ row }) => {
      return `${row.original.sentCount}/${row.original.failedCount}/${row.original.totalCount}`
    },
    meta: {
      class: {
        td: 'text-center',
      },
    },
  },
  {
    accessorKey: 'status',
    header: 'Статус',
  },
  {
    accessorKey: 'actions',
    header: 'Действия',
    meta: {
      class: {
        th: 'text-right',
      },
    },
  },
]
</script>
