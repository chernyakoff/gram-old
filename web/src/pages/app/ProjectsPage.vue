<template>
  <UDashboardPanel id="projects">
    <template #header>
      <UDashboardNavbar :title="title" :ui="{ right: 'gap-3' }">
        <template #leading>
          <UDashboardSidebarCollapse />
        </template>
        <template #right>
          <AddModal @completed="refresh" />
        </template>
      </UDashboardNavbar>
    </template>
    <template #body>
      <div class="flex flex-wrap items-center justify-end gap-1.5"></div>
      <UTable
        ref="table"
        v-model:column-filters="columnFilters"
        v-model:column-visibility="columnVisibility"
        class="shrink-0"
        :data="projects ?? []"
        :columns="columns"
        :loading="loading"
        :ui="{
          base: 'table-fixed border-separate border-spacing-0',
          thead: '[&>tr]:bg-elevated/50 [&>tr]:after:content-none',
          tbody: '[&>tr]:last:[&>td]:border-b-0',
          th: 'py-2 first:rounded-l-lg last:rounded-r-lg border-y border-default first:border-l last:border-r',
          td: 'border-b border-default',
        }"
      />
    </template>
  </UDashboardPanel>
</template>
<script setup lang="ts">
import AddModal from '@/components/proxies/AddModal.vue'

import type { TableColumn } from '@nuxt/ui'
import { resolveComponent, h, ref } from 'vue'
import { useTitle, useDateFormat } from '@vueuse/core'

import type { Table } from '@tanstack/vue-table'

const UCheckbox = resolveComponent('UCheckbox')

const loading = false

const title = 'Проекты'
useTitle(title)

const columnFilters = ref([
  {
    id: 'host',
    value: '',
  },
])
const columnVisibility = ref()

function refresh() {}

const projects = [
  {
    id: 1,
    name: 'Проект А',
    description: 'Описание проекта А',
    accounts: 12,
    dialogs: 8,
    status: 'Активен',
    createdAt: '2025-01-15T10:23:00Z',
  },
  {
    id: 2,
    name: 'Проект Б',
    description: 'Описание проекта Б',
    accounts: 7,
    dialogs: 5,
    status: 'Неактивен',
    createdAt: '2025-03-22T14:45:00Z',
  },
  {
    id: 3,
    name: 'Проект В',
    description: 'Описание проекта В',
    accounts: 5,
    dialogs: 12,
    status: 'Активен',
    createdAt: '2025-05-10T09:12:00Z',
  },
  {
    id: 4,
    name: 'Проект Г',
    description: 'Описание проекта Г',
    accounts: 20,
    dialogs: 15,
    status: 'В процессе',
    createdAt: '2025-06-05T16:30:00Z',
  },
  {
    id: 5,
    name: 'Проект Д',
    description: 'Описание проекта Д',
    accounts: 3,
    dialogs: 9,
    status: 'Архив',
    createdAt: '2025-08-01T11:00:00Z',
  },
]

const columns: TableColumn[] = [
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
        ariaLabel: 'Выбрать проекты',
      }),
  },
  {
    accessorKey: 'id',
    header: 'ID',
  },
  {
    accessorKey: 'name',
    header: 'Название',
  },
  {
    accessorKey: 'description',
    header: 'Описание',
  },
  {
    accessorKey: 'accounts',
    header: 'Аккаунтов',
  },
  {
    accessorKey: 'dialogs',
    header: 'Логин',
  },
  {
    accessorKey: 'status',
    header: 'Статус',
  },
  {
    accessorKey: 'createdAt',
    header: 'Создан',
    cell: ({ row }) => useDateFormat(row.original.createdAt, 'DD.MM.YY').value,
  },
]
</script>
