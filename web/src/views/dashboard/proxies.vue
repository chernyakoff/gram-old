<template>
  <UDashboardPanel id="proxies">
    <template #header>
      <UDashboardNavbar :title="title" :ui="{ right: 'gap-3' }">
        <template #leading>
          <UDashboardSidebarCollapse />
        </template>
        <template #right>
          <AddProxiesModal @completed="refresh" />
        </template>
      </UDashboardNavbar>
    </template>
    <template #body>
      <div class="mx-auto bg-dimmed">
        <div class="flex flex-wrap items-center justify-end gap-1.5 mb-4">
          <CheckProxiesModal :selected-ids="selectedIds" @completed="refresh" />
          <ChangeCountryModal :selected-ids="selectedIds" @close="refresh" />
          <DeleteProxiesModal :selected-ids="selectedIds" @close="refresh" />
        </div>
        <UTable
          ref="table"
          v-model:column-visibility="columnVisibility"
          v-model:sorting="sorting"
          class="shrink-0"
          :data="proxies ?? []"
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
          <template #status-cell="{ row }"><ProxyStatusBadge :proxy="row.original" /></template>
          <template #accounts-cell="{ row }">
            <div v-if="row.original.account" class="p-2 text-sm">
              {{
                row.original.account.username
                  ? `@${row.original.account.username}`
                  : `ID: ${row.original.account.id}`
              }}
            </div>
          </template>
        </UTable>
      </div>
    </template>
  </UDashboardPanel>
</template>
<script setup lang="ts">
import { useTitle, useDateFormat } from '@vueuse/core'
import type { TableColumn } from '@nuxt/ui'
import { onMounted, ref, h, resolveComponent } from 'vue'
import DeleteProxiesModal from '@/components/dashboard/proxies/delete-modal.vue'
import ChangeCountryModal from '@/components/dashboard/proxies/country-modal.vue'
import AddProxiesModal from '@/components/dashboard/proxies/add-modal.vue'
import CheckProxiesModal from '@/components/dashboard/proxies/check-modal.vue'
import ProxyStatusBadge from '@/components/dashboard/proxies/status-badge.vue'
import { useProxies } from '@/composables/use-proxies'
import { useTableSelection } from '@/composables/table/use-selection.bak'
import type { ProxyOut } from '@/types/openapi'
import type { Column, SortingFn } from '@tanstack/vue-table'

const title = 'Прокси'
useTitle(title)

const { proxies, get, loading } = useProxies()

onMounted(() => get())

const columnVisibility = ref()
const sorting = ref<{ id: string; desc: boolean }[]>([])

const { tableApi, selectedIds, selectionColumn } = useTableSelection<ProxyOut>('table')

const refresh = () => {
  tableApi.value?.setRowSelection({})
  get()
}

const UButton = resolveComponent('UButton')

function getHeader(column: Column<ProxyOut>, label: string) {
  const isSorted = column.getIsSorted()

  return h(UButton, {
    color: 'neutral',
    variant: 'ghost',
    label,
    icon: isSorted
      ? isSorted === 'asc'
        ? 'i-lucide-arrow-up-narrow-wide'
        : 'i-lucide-arrow-down-wide-narrow'
      : 'i-lucide-arrow-up-down',
    class: '-mx-2.5',
    onClick: () => column.toggleSorting(column.getIsSorted() === 'asc'),
  })
}

type ProxyStatus = 'working' | 'unstable' | 'disabled'

function getProxyStatus(proxy: ProxyOut): ProxyStatus {
  if (!proxy.active) return 'disabled'
  if (proxy.failures > 0) return 'unstable'
  return 'working'
}

const proxyStatusSortingFn: SortingFn<ProxyOut> = (rowA, rowB) => {
  const rank: Record<ProxyStatus, number> = {
    working: 0,
    unstable: 1,
    disabled: 2,
  }

  return rank[getProxyStatus(rowA.original)] - rank[getProxyStatus(rowB.original)]
}

const proxyAccountSortingFn: SortingFn<ProxyOut> = (rowA, rowB) => {
  const a = rowA.original.account
  const b = rowB.original.account

  if (!a && !b) return 0
  if (!a) return 1
  if (!b) return -1

  const aUser = (a.username ?? '').toLowerCase()
  const bUser = (b.username ?? '').toLowerCase()

  if (aUser && bUser) return aUser.localeCompare(bUser, 'ru')
  if (aUser) return -1
  if (bUser) return 1

  return a.id - b.id
}

const columns: TableColumn<ProxyOut>[] = [
  selectionColumn(),

  {
    id: 'status',
    header: ({ column }) => getHeader(column, 'Статус'),
    accessorFn: (row) => getProxyStatus(row),
    sortingFn: proxyStatusSortingFn,
  },
  {
    accessorKey: 'country',
    header: ({ column }) => getHeader(column, 'Страна'),
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
    id: 'accounts',
    header: ({ column }) => getHeader(column, 'Аккаунт'),
    accessorFn: (row) => row.account?.username ?? row.account?.id ?? null,
    sortingFn: proxyAccountSortingFn,
  },
  {
    accessorKey: 'createdAt',
    header: 'Добавлен',
    cell: ({ row }) => useDateFormat(row.original.createdAt, 'DD.MM.YY').value,
  },
]
</script>
