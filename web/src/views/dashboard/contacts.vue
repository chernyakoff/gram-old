<template>
  <UDashboardPanel id="contacts">
    <template #header>
      <UDashboardNavbar :title="title" :ui="{ right: 'gap-3' }">
        <template #leading>
          <UDashboardSidebarCollapse />
        </template>
        <template #right>
          <AddContactsModal @close="refresh" />
        </template>
      </UDashboardNavbar>
    </template>
    <template #body>
      <div class="flex flex-wrap items-center justify-end gap-1.5">
        <DeleteContactsModal :selected-ids="selectedIds" @close="refresh" />
      </div>
      <UTable
        ref="table"
        v-model:pagination="pagination"
        v-model:column-filters="columnFilters"
        v-model:column-visibility="columnVisibility"
        class="shrink-0"
        :pagination-options="{
          getPaginationRowModel: getPaginationRowModel(),
        }"
        :data="contacts ?? []"
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
        <template #username-cell="{ row }">
          <a class="text-sm" :href="`https://t.me/${row.original.username}`" target="_blank">
            {{ row.original.username }}
          </a>
        </template>
      </UTable>
      <div class="flex justify-center border-t border-default pt-4">
        <UPagination
          :default-page="(tableApi?.getState().pagination.pageIndex || 0) + 1"
          :items-per-page="tableApi?.getState().pagination.pageSize"
          :total="tableApi?.getFilteredRowModel().rows.length"
          @update:page="(p) => tableApi?.setPageIndex(p - 1)"
        />
      </div>
    </template>
  </UDashboardPanel>
</template>
<script setup lang="ts">
import type { TableColumn } from '@nuxt/ui'
import { ref, onMounted } from 'vue'
import { useTitle, useDateFormat } from '@vueuse/core'
import { getPaginationRowModel } from '@tanstack/vue-table'
import AddContactsModal from '@/components/dashboard/contacts/add-modal.vue'
import DeleteContactsModal from '@/components/dashboard/contacts/delete-modal.vue'

import { useContacts } from '@/composables/use-mailings'
import { useTableSelection } from '@/composables/table/use-selection'
import type { ContactOut } from '@/types/openapi'

const { contacts, get, loading } = useContacts()

const title = 'Контакты'
useTitle(title)

onMounted(() => get())

// - drawer

const refresh = () => {
  tableApi.value?.setRowSelection({})
  get()
}

//- table
const pagination = ref({
  pageIndex: 0,
  pageSize: 10,
})
const columnFilters = ref([{ id: 'username', value: '' }])
const columnVisibility = ref()
const { tableApi, selectedIds, selectionColumn } = useTableSelection<ContactOut>('table', 'uid')

const columns: TableColumn<ContactOut>[] = [
  selectionColumn(),

  {
    accessorKey: 'projectName',
    header: 'Проект',
    cell: ({ row }) => {
      return row.original.project.name
    },
  },
  {
    accessorKey: 'username',
    header: 'Юзернейм',
  },
  {
    accessorKey: 'firstName',
    header: 'Имя',
  },
  {
    accessorKey: 'lastName',
    header: 'Фамилия',
  },
  {
    accessorKey: 'createdAt',
    header: 'Создан',
    cell: ({ row }) => useDateFormat(row.original.createdAt, 'DD.MM.YY').value,
  },
]
</script>
