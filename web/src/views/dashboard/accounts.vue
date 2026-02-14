<template>
  <UDashboardPanel id="accounts">
    <template #header>
      <UDashboardNavbar :title="title" :ui="{ right: 'gap-3' }">
        <template #leading>
          <UDashboardSidebarCollapse />
        </template>
        <template #right>
          <AddAccountsModal @completed="refresh" />
        </template>
      </UDashboardNavbar>
    </template>
    <template #body>
      <div class="flex flex-wrap items-center justify-end gap-1.5">
        <SetLimitmodal :selected-ids="selectedIds" @close="refresh" />
        <CheckModal :selected-ids="selectedIds" @completed="refresh" />
        <BindProjectModal :selected-ids="selectedIds" @close="refresh" />
        <DeleteAccountsModal :selected-ids="selectedIds" @close="refresh" />
      </div>
      <UTable
        ref="table"
        v-model:column-filters="columnFilters"
        v-model:column-visibility="columnVisibility"
        class="shrink-0"
        :data="accounts ?? []"
        :columns="columns"
        :loading="loading"
        v-model:sorting="sorting"
        :ui="{
          base: 'table-fixed border-separate border-spacing-0',
          thead: '[&>tr]:bg-elevated/50 [&>tr]:after:content-none',
          tbody: '[&>tr]:last:[&>td]:border-b-0',
          th: 'py-2 first:rounded-l-lg last:rounded-r-lg border-y border-default first:border-l last:border-r',
          td: 'border-b border-default',
        }">
        <template #status-cell="{ row }">
          <AccountStatusBadge :account="row.original" />
        </template>
        <template #project-cell="{ row }">
          {{ row.original.project?.name ?? 'не назначен' }}
        </template>
        <template #premium-cell="{ row }">
          <div class="flex items-center gap-1 justify-center">
            <template v-if="row.original.busy">
              <UIcon
                name="i-lucide-loader-circle"
                class="h-6 w-6 animate-spin text-warning"
                title="Аккаунт в работе"
                aria-label="Аккаунт в работе" />
            </template>
            <template v-else-if="row.original.premium && row.original.premiumStopped">
              <UIcon name="bxs:star" class="h-6 w-6 text-gray-400" />
            </template>
            <template v-else-if="!row.original.premium">
              <button class="flex items-center gap-1" @click="openPremiumDrawer(row.original)">
                <UIcon name="bx:cart" class="h-6 w-6" />
              </button>
            </template>
            <template v-else>
              <StopPremiumModal :account="row.original" @completed="refresh" />
            </template>
          </div>
        </template>
        <template #name-cell="{ row }">
          <div
            class="flex items-center gap-3"
            :class="row.original.busy ? 'opacity-60 cursor-not-allowed' : 'cursor-pointer'"
            @click="openDrawer(row.original)">
            <UButton
              v-if="row.original.photos.length"
              class="rounded-full"
              color="neutral"
              variant="link">
              <template #default>
                <UAvatar :src="row.original.photos[0]?.url" class="h-8 w-8" />
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
                <template v-if="row.original.username">
                  <a
                    class="text-sm"
                    :class="row.original.busy ? 'pointer-events-none' : ''"
                    :href="`https://t.me/${row.original.username}`"
                    target="_blank"
                    @click.stop> @{{ row.original.username }} </a>
                </template>
                <template v-else>
                  <span class="text-sm text-gray-400">(нет username)</span>
                </template>
              </p>
            </div>
          </div>
        </template>
        <template #outDailyLimit-cell="{ row }">
          <span v-if="!row.original.isDynamicLimit">
            {{ row.original.outDailyLimit }}
          </span>
          <span v-else>
            {{ row.original.outDailyLimit }} ({{ row.original.dynamicDailyLimit }}) </span>
        </template>
      </UTable>
    </template>
  </UDashboardPanel>
  <AccountDrawer v-if="selectedAccountId !== null" v-model:open="drawerOpen" :accountId="selectedAccountId" :key="selectedAccountId" @completed="refresh" />
  <PremiumDrawer v-if="selectedAccountId !== null" v-model:open="premiumDrawerOpen" :accountId="selectedAccountId" :key="selectedAccountId" @completed="refresh" />
</template>
<script setup lang="ts">
import DeleteAccountsModal from '@/components/dashboard/accounts/delete-modal.vue'
import AddAccountsModal from '@/components/dashboard/accounts/add-modal.vue'
import BindProjectModal from '@/components/dashboard/accounts/project-modal.vue'
import SetLimitmodal from '@/components/dashboard/accounts/limit-modal.vue'
import CheckModal from '@/components/dashboard/accounts/check-modal.vue'
import AccountDrawer from '@/components/dashboard/accounts/drawer.vue'
import PremiumDrawer from '@/components/dashboard/accounts/premium-drawer.vue'
import StopPremiumModal from '@/components/dashboard/accounts/stop-premium-modal.vue'
import AccountStatusBadge from '@/components/dashboard/accounts/status-badge.vue'

import { useAccounts } from '@/composables/use-accounts'
import { useTitle, useDateFormat } from '@vueuse/core'

import type { TableColumn } from '@nuxt/ui'
import { ref, onMounted, onUnmounted, onActivated, onDeactivated, h, resolveComponent } from 'vue'

import { useTableSelection } from '@/composables/table/use-selection'
import type { AccountOut, AccountStateOut } from '@/types/openapi'
import type { Column, SortingFn } from '@tanstack/vue-table'

const title = 'Аккаунты'
useTitle(title)
const { get, state, accounts, loading } = useAccounts()
const toast = useToast()

// Drawer управление
const drawerOpen = ref(false)
const premiumDrawerOpen = ref(false)

const selectedAccountId = ref<number | null>(null)

function openDrawer (account: AccountOut) {
  if (account.busy) {
    toast.add({
      title: 'Аккаунт в работе',
      color: 'warning',
    })
    return
  }
  selectedAccountId.value = account.id
  drawerOpen.value = true
}

function openPremiumDrawer (account: AccountOut) {
  if (account.busy) {
    toast.add({
      title: 'Аккаунт в работе',
      color: 'warning',
    })
    return
  }
  if (!account.username) {
    toast.add({
      title: 'Нужен username',
      description: 'Для покупки premium установите аккаунту username',
      color: 'warning',
    })
    return
  }
  selectedAccountId.value = account.id
  premiumDrawerOpen.value = true
}

const columnFilters = ref([{ id: 'phone', value: '' }])
const columnVisibility = ref()
const UIcon = resolveComponent('UIcon')
const { tableApi, selectedIds, selectionColumn } = useTableSelection<AccountOut>('table', 'id', {
  isSelectable: (row) => !row.busy,
  renderNonSelectable: () => h('div', { class: 'flex items-center justify-center w-full' }, [
    h(UIcon, {
      name: 'i-lucide-loader-circle',
      class: 'h-4 w-4 animate-spin text-warning',
      title: 'Аккаунт в работе',
      'aria-label': 'Аккаунт в работе',
    }),
  ]),
})

const STATE_POLL_INTERVAL = 5000
const stateSyncInFlight = ref(false)
let statePollTimer: ReturnType<typeof setInterval> | null = null

function cleanupBusySelection () {
  if (!tableApi.value) return
  tableApi.value.getSelectedRowModel().rows.forEach((row) => {
    if (row.original.busy) {
      row.toggleSelected(false)
    }
  })
}

function applyStateUpdates (states: AccountStateOut[]) {
  const stateById = new Map(states.map((item) => [item.id, item]))
  let changed = false

  accounts.value.forEach((account) => {
    const next = stateById.get(account.id)
    if (!next) return

    if (
      account.busy !== next.busy ||
      account.status !== next.status ||
      account.premium !== next.premium
    ) {
      account.busy = next.busy
      account.status = next.status
      account.premium = next.premium
      changed = true
    }
  })

  if (changed) {
    cleanupBusySelection()
  }
}

async function syncState () {
  if (stateSyncInFlight.value || !accounts.value.length) return

  stateSyncInFlight.value = true
  try {
    const states = await state()
    applyStateUpdates(states)
  } catch (e) {
    console.error('accounts state sync failed', e)
  } finally {
    stateSyncInFlight.value = false
  }
}

function startStatePolling () {
  if (statePollTimer) return
  statePollTimer = setInterval(() => {
    void syncState()
  }, STATE_POLL_INTERVAL)
}

function stopStatePolling () {
  if (!statePollTimer) return
  clearInterval(statePollTimer)
  statePollTimer = null
}

onMounted(async () => {
  await get()
  void syncState()
  startStatePolling()
})

onActivated(() => {
  startStatePolling()
  void syncState()
})

onDeactivated(() => {
  stopStatePolling()
})

onUnmounted(() => {
  stopStatePolling()
})

const refresh = async () => {
  tableApi.value?.setRowSelection({})
  await get()
  void syncState()
}

const columnCentered = {
  meta: {
    class: {
      th: 'text-center',
      td: 'text-center',
    },
  },
}


const UButton = resolveComponent('UButton')

function getHeader (column: Column<AccountOut>, label: string) {
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
    onClick: () => column.toggleSorting(column.getIsSorted() === 'asc')
  })

}


const sorting = ref([
  {
    id: 'id',
    desc: false
  }
])

const limitSortingFn: SortingFn<AccountOut> = (rowA, rowB) => {
  const getLimit = (row: AccountOut) =>
    row.isDynamicLimit ? row.dynamicDailyLimit : row.outDailyLimit

  const valueA = getLimit(rowA.original) ?? 0  // null/undefined -> 0
  const valueB = getLimit(rowB.original) ?? 0

  return valueA - valueB
}

const columns: TableColumn<AccountOut>[] = [
  selectionColumn(),
  {
    accessorKey: 'id',
    header: "ID"

  },
  {
    accessorKey: 'status',
    header: ({ column }) => getHeader(column, 'Статус'),
    ...columnCentered,
  },
  {
    accessorKey: 'project',
    header: ({ column }) => getHeader(column, 'Проект'),

  },
  {
    accessorKey: 'phone',
    header: 'Телефон',
  },
  {
    accessorKey: 'country',
    header: ({ column }) => getHeader(column, 'Страна'),
  },
  {
    accessorKey: 'name',
    header: 'Имя',
    meta: {
      class: {
        th: 'text-center',
      },
    },
  },
  {
    accessorKey: 'premium',

    header: ({ column }) => getHeader(column, 'Премиум'),
    ...columnCentered,
  },
  {
    accessorKey: 'premiumedAt',
    header: 'Прем. куплен',
    cell: ({ row }) => {
      if (row.original.premiumedAt) {
        return useDateFormat(row.original.premiumedAt, 'DD.MM.YY').value
      } else {
        return "---"
      }

    },
    ...columnCentered,
  },
  {
    accessorKey: 'outDailyLimit',
    header: ({ column }) => getHeader(column, 'Лимит'),
    ...columnCentered,
    sortingFn: limitSortingFn,

  },
  {
    accessorKey: 'dialogsCount',
    header: ({ column }) => getHeader(column, '💬'),
    ...columnCentered,

  },
  /*  {
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
    accessorKey: 'busy',
    header: 'Статус',
  },
  {
    accessorKey: 'active',
    header: 'Состояние',
  }, */
  {
    accessorKey: 'createdAt',

    header: ({ column }) => getHeader(column, 'Загружен'),
    cell: ({ row }) => useDateFormat(row.original.createdAt, 'DD.MM.YY').value,
  },
]
</script>
