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
          }">
          <template #status-cell="{ row }">
            <UBadge
              class="opacity-80"
              :label="getStatusInfo(row.original.status).label"
              :color="getStatusInfo(row.original.status).color" />
          </template>
          <template #actions-cell="{ row }">
            <div class="flex items-center justify-end gap-2">
              <USwitch
                title="Вкл/Выкл"
                :modelValue="row.original.active"
                @update:modelValue="(val: boolean) => toggleActive(row.original, val)" />
              <UButton
                variant="ghost"
                icon="clarity:clone-line"
                title="Перенести в другой проект"
                @click="openProjectModal(row.original as MailingOut)" />
              <UButton
                variant="ghost"
                icon="bx:trash"
                title="Удалить рассылку"
                @click="openDeleteModal(row.original as MailingOut)" />
            </div>
          </template>
        </UTable>
      </div>
    </template>
  </UDashboardPanel>
  <ConfirmModal v-model="isConfirmModalOpen" title="Подтверждение удаления" :description="`Вы уверены, что хотите удалить '${selectedItem?.name}'?`" @confirm="handleDelete" />
  <ProjectModal
    v-model:open="isProjectModalOpen"
    :mailing-id="selectedTransferItem?.id"
    :current-project-id="selectedTransferItem?.project.id"
    :pending-count="selectedPendingCount"
    @close="refresh" />
</template>
<script setup lang="ts">
import { useTitle } from '@vueuse/core'
import AddMailingModal from '@/components/dashboard/mailings/add-modal.vue'
import ProjectModal from '@/components/dashboard/mailings/project-modal.vue'
import ConfirmModal from '@/components/shared/confirm-modal.vue'
import { useMailings } from '@/composables/use-mailings'
import { onMounted, ref } from 'vue'
import type { MailingOut } from '@/types/openapi'
import type { TableColumn } from '@nuxt/ui'
const title = 'Рассылки'
useTitle(title)

const isConfirmModalOpen = ref(false)
const isProjectModalOpen = ref(false)

const selectedItem = ref<MailingOut>()
const selectedTransferItem = ref<MailingOut>()
const selectedPendingCount = ref(0)

const { mailings, get, loading, del, toggle } = useMailings()

onMounted(() => get())

const columnFilters = ref([{ id: 'name', value: '' }])
const columnVisibility = ref()

const refresh = () => {
  get()
}

async function handleDelete () {
  if (selectedItem.value) {
    await del([selectedItem.value.id])
    await get()
  }
}

const statusMap = {
  draft: { label: 'Создана', color: 'warning' },
  running: { label: 'Запущена', color: 'primary' },
  finished: { label: 'Завершёна', color: 'success' },
  cancelled: { label: 'Отменёна', color: 'error' },
} as const

function openDeleteModal (item: MailingOut) {
  selectedItem.value = item
  isConfirmModalOpen.value = true
}

function openProjectModal (item: MailingOut) {
  selectedTransferItem.value = item
  selectedPendingCount.value = Math.max(
    (item.totalCount ?? 0) - (item.sentCount ?? 0) - (item.failedCount ?? 0),
    0,
  )
  isProjectModalOpen.value = true
}

type Status = keyof typeof statusMap

function getStatusInfo (status: string) {
  return statusMap[status as Status] ?? { label: 'Неизвестно', color: 'default' }
}

const toggleActive = async (mailing: MailingOut, value: boolean) => {
  mailing.active = value
  await toggle(mailing.id, value)
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
  },
]
</script>
