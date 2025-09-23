<template>
  <UDashboardPanel id="proxies">
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
      <div class="flex flex-wrap items-center justify-end gap-1.5">
        <DeleteModal :selected-ids="selectedIds" @close="refresh" />
      </div>
      <UTable
        ref="table"
        v-model:column-filters="columnFilters"
        v-model:column-visibility="columnVisibility"
        class="shrink-0"
        :data="proxies ?? []"
        :columns="columns"
        :loading="loading"
        :ui="{
          base: 'table-fixed border-separate border-spacing-0',
          thead: '[&>tr]:bg-elevated/50 [&>tr]:after:content-none',
          tbody: '[&>tr]:last:[&>td]:border-b-0',
          th: 'py-2 first:rounded-l-lg last:rounded-r-lg border-y border-default first:border-l last:border-r',
          td: 'border-b border-default'
        }" />
    </template>
  </UDashboardPanel>
</template>
<script setup lang="ts">
import AddModal from '@/components/proxies/AddModal.vue'
import DeleteModal from '@/components/proxies/DeleteModal.vue'
import { useTitle, useDateFormat } from '@vueuse/core'
import type { TableColumn } from '@nuxt/ui'
import { resolveComponent, h, ref, useTemplateRef, onMounted } from 'vue'
import { useProxies } from '@/composables/useProxies'
import { computed } from 'vue'
import type { Table } from '@tanstack/vue-table'

/*
 v-model:pagination="pagination"
        :pagination-options="{
          getPaginationRowModel: getPaginationRowModel()
        }"
*/
const title = "Прокси"
useTitle(title)

const { get, proxies, loading } = useProxies()

const UCheckbox = resolveComponent('UCheckbox')

const columnFilters = ref([{
  id: 'host',
  value: ''
}])
const columnVisibility = ref()


type TableData = Record<string, unknown> & { id: number }
const table = useTemplateRef<{ tableApi: Table<TableData> }>('table')


const selectedIds = computed(() => {
  if (!table.value?.tableApi) return []
  return table.value.tableApi.getSelectedRowModel().rows.map(row => row.original.id)
})

onMounted(() => get())

const refresh = () => {
  table.value?.tableApi?.setRowSelection({});
  get()
}

const columns: TableColumn<Proxy>[] = [
  {
    id: 'select',
    header: ({ table }) =>
      h(UCheckbox, {
        'modelValue': table.getIsSomePageRowsSelected()
          ? 'indeterminate'
          : table.getIsAllPageRowsSelected(),
        'onUpdate:modelValue': (value: boolean | 'indeterminate') =>
          table.toggleAllPageRowsSelected(!!value),
        'ariaLabel': 'Выбрать всё'
      }),
    cell: ({ row }) =>
      h(UCheckbox, {
        'modelValue': row.getIsSelected(),
        'onUpdate:modelValue': (value: boolean | 'indeterminate') => row.toggleSelected(!!value),
        'ariaLabel': 'Выбрать прокси'
      })
  },
  {
    accessorKey: 'id',
    header: 'ID'
  },
  {
    accessorKey: 'country',
    header: 'Страна',

  },
  {
    accessorKey: 'host',
    header: 'Хост',

  },
  {
    accessorKey: 'port',
    header: 'Порт',
  },
  {
    accessorKey: 'username',
    header: 'Логин',
  },
  {
    accessorKey: 'password',
    header: 'Пароль',
  },
  {
    accessorKey: 'createdAt',
    header: 'Загружен',
    cell: ({ row }) => useDateFormat(row.original.createdAt, 'DD.MM.YY').value

  },
]

</script>
