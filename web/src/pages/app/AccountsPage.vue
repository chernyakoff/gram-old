<template>
  <UDashboardPanel id="accounts">
    <template #header>
      <UDashboardNavbar :title="title" :ui="{ right: 'gap-3' }">
        <template #leading>
          <UDashboardSidebarCollapse />
        </template>
        <template #right>
          <UploadModal @completed="refresh" />
        </template>
      </UDashboardNavbar>
    </template>
    <template #body>
      <div class="flex flex-wrap items-center justify-end gap-1.5">
        <DeleteModal :selected-ids="selectedIds" @close="refresh" />
        <UDropdownMenu
          :items="
            table?.tableApi
              ?.getAllColumns()
              .filter((column: any) => column.getCanHide())
              .map((column: any) => ({
                label: upperFirst(column.id),
                type: 'checkbox' as const,
                checked: column.getIsVisible(),
                onUpdateChecked(checked: boolean) {
                  table?.tableApi?.getColumn(column.id)?.toggleVisibility(!!checked)
                },
                onSelect(e?: Event) {
                  e?.preventDefault()
                },
              }))
          "
          :content="{ align: 'end' }"
        >
          <UButton
            label="Столбцы"
            color="neutral"
            variant="outline"
            trailing-icon="i-lucide-settings-2"
          />
        </UDropdownMenu>
      </div>
      <UTable
        ref="table"
        v-model:column-filters="columnFilters"
        v-model:column-visibility="columnVisibility"
        class="shrink-0"
        :data="accounts ?? []"
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
          <div class="flex items-center gap-3" @click="openDrawer(row.original.id)">
            <UButton
              v-if="row.original.photos.length"
              class="rounded-full"
              color="neutral"
              variant="link"
            >
              <template #default>
                <UAvatar :src="row.original.photos[0].url" class="h-8 w-8" />
              </template>
            </UButton>
            <UButton v-else class="rounded-full" color="neutral" variant="link">
              <template #default>
                <UIcon name="i-lucide-circle-user" class="h-8 w-8" />
              </template>
            </UButton>
            <div>
              <p class="font-medium text-highlighted">
                {{ row.original.firstName }} {{ row.original.lastName }}
              </p>
              <p>
                <a class="text-sm" :href="`https://t.me/${row.original.username}`" target="_blank">
                  @{{ row.original.username }}
                </a>
              </p>
            </div>
          </div>
        </template>
      </UTable>
    </template>
  </UDashboardPanel>
  <AccountDrawer
    v-if="selectedAccountId !== null"
    v-model:open="drawerOpen"
    :account_id="selectedAccountId"
    :key="selectedAccountId"
    @completed="refresh"
  />
</template>
<script setup lang="ts">
import UploadModal from '@/components/accounts/UploadModal.vue'
import DeleteModal from '@/components/accounts/DeleteModal.vue'

import AccountDrawer from '@/components/accounts/AccountDrawer.vue'
import { useAccounts } from '@/composables/useAccounts'
import { useTitle, useDateFormat } from '@vueuse/core'
import type { Table } from '@tanstack/vue-table'
import type { TableColumn } from '@nuxt/ui'
import { resolveComponent, h, ref, useTemplateRef, onMounted, computed } from 'vue'
import { upperFirst } from 'scule'

const title = 'Аккаунты'
useTitle(title)
const { get, accounts, loading } = useAccounts()

const UCheckbox = resolveComponent('UCheckbox')

const columnFilters = ref([
  {
    id: 'phone',
    value: '',
  },
])
const columnVisibility = ref()

type TableData = Record<string, unknown> & { id: number }
const table = useTemplateRef<{ tableApi: Table<TableData> }>('table')

const selectedIds = computed(() => {
  if (!table.value?.tableApi) return []
  return table.value.tableApi.getSelectedRowModel().rows.map((row) => row.original.id)
})

onMounted(() => get())

// Drawer управление
const drawerOpen = ref(false)
const selectedAccountId = ref<number | null>(null)

function openDrawer(id: number) {
  selectedAccountId.value = id
  drawerOpen.value = true
}

const refresh = () => {
  table.value?.tableApi?.setRowSelection({})
  get()
}

const columns: TableColumn<Account>[] = [
  {
    id: 'select',
    header: ({ table }) =>
      h(UCheckbox, {
        modelValue: table.getIsSomePageRowsSelected()
          ? 'indeterminate'
          : table.getIsAllPageRowsSelected(),
        'onUpdate:modelValue': (value: boolean | 'indeterminate') =>
          table.toggleAllPageRowsSelected(!!value),
        ariaLabel: 'Выбрать всё',
      }),
    cell: ({ row }) =>
      h(UCheckbox, {
        modelValue: row.getIsSelected(),
        'onUpdate:modelValue': (value: boolean | 'indeterminate') => row.toggleSelected(!!value),
        ariaLabel: 'Выбрать прокси',
      }),
  },
  {
    accessorKey: 'id',
    header: 'ID',
  },
  {
    accessorKey: 'phone',
    header: 'Телефон',
  },
  {
    accessorKey: 'country',
    header: 'Страна',
  },
  {
    accessorKey: 'name',
    header: 'Имя',
  },
  {
    accessorKey: 'about',
    header: 'Профиль',
  },
  {
    accessorKey: 'twofa',
    header: 'Пароль',
  },
  {
    accessorKey: 'channel',
    header: 'Канал',
  },
  {
    accessorKey: 'premium',
    header: 'Премиум',
  },
  {
    accessorKey: 'busy',
    header: 'Статус',
  },
  {
    accessorKey: 'active',
    header: 'Состояние',
  },
  {
    accessorKey: 'createdAt',
    header: 'Загружен',
    cell: ({ row }) => useDateFormat(row.original.createdAt, 'DD.MM.YY').value,
  },
]
</script>
