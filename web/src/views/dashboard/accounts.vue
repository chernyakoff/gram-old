<template>
  <UDashboardPanel id="accounts">
    <template #header>
      <UDashboardNavbar :title="title" :ui="navbarUi">
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
        <div class="mr-auto text-sm text-muted">
          {{ accountsCountLabel }}
        </div>
        <AccountsBulkActionsMenu :selected-ids="selectedIds" @completed="refresh" />
        <UDropdownMenu
          :items="columnVisibilityItems"
          :content="dropdownContent">
          <UButton
            label="Колонки"
            color="neutral"
            variant="outline"
            trailing-icon="i-lucide-chevron-down"
            aria-label="Columns select dropdown" />
        </UDropdownMenu>
      </div>
      <UTable
        ref="table"
        v-model:column-filters="columnFilters"
        v-model:column-visibility="columnVisibility"
        class="shrink-0"
        :data-hold-tick="holdTick"
        :data="accounts"
        :columns="columns"
        :loading="loading"
        v-model:sorting="sorting"
        :ui="tableUi">
        <template #status-cell="{ row }">
          <AccountStatusBadge :account="row.original" />
        </template>
        <template #proxy-cell="{ row }">
          <div class="flex items-center justify-center">
            <UPopover v-if="row.original.proxy" mode="hover">
              <UIcon
                name="i-lucide-server"
                class="h-5 w-5 text-muted"
                aria-label="Прокси"
                title="Прокси" />
              <template #content>
                <div class="p-2 text-sm">
                  {{ row.original.proxy }}
                </div>
              </template>
            </UPopover>
          </div>
        </template>
        <template #project-cell="{ row }">
          <div class="project-cell-text" lang="ru">
            {{ row.original.project?.name ?? 'не назначен' }}
          </div>
        </template>
        <template #premium-cell="{ row }">
          <div
            class="flex items-center gap-1 justify-center"
            :class="(row.original.busy || isInHold(row.original)) ? 'cursor-not-allowed' : ''"
            :title="row.original.busy ? 'Аккаунт в работе' : isInHold(row.original) ? `Отлежка до ${holdUntilLabel(row.original) ?? '---'}` : undefined">
            <template v-if="row.original.premium && row.original.premiumStopped">
              <UIcon name="bxs:star" class="h-6 w-6 text-gray-400" />
            </template>
            <template v-else-if="!row.original.premium">
              <button
                class="flex items-center gap-1"
                :class="(row.original.busy || isInHold(row.original)) ? 'cursor-not-allowed' : 'cursor-pointer'"
                :disabled="row.original.busy || isInHold(row.original)"
                :aria-disabled="row.original.busy || isInHold(row.original)"
                :title="row.original.busy ? 'Аккаунт в работе' : isInHold(row.original) ? `Отлежка до ${holdUntilLabel(row.original) ?? '---'}` : undefined"
                @click="openPremiumDrawer(row.original)">
                <UIcon name="bx:cart" class="h-6 w-6" />
              </button>
            </template>
            <template v-else>
              <StopPremiumModal :account="row.original" :disabled="row.original.busy || isInHold(row.original)" @completed="refresh" />
            </template>
          </div>
        </template>
        <template #name-cell="{ row }">
          <div
            class="flex items-center gap-3"
            :class="(row.original.busy || isInHold(row.original)) ? 'opacity-60 cursor-not-allowed' : 'cursor-pointer'"
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
            <div class="min-w-0">
              <template v-if="isInHold(row.original)">
                <p
                  class="font-medium text-muted whitespace-nowrap"
                  :title="`Отлежка до ${holdUntilLabel(row.original) ?? '---'}`"> 💤 {{ holdRemainingLabel(row.original) ?? '---' }}
                </p>
              </template>
              <template v-else>
                <p
                  class="font-medium text-highlighted truncate max-w-[260px]"
                  :title="`${row.original.firstName ?? ''} ${row.original.lastName ?? ''}`">
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
              </template>
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
import AddAccountsModal from '@/components/dashboard/accounts/add-modal.vue'
import AccountDrawer from '@/components/dashboard/accounts/drawer.vue'
import PremiumDrawer from '@/components/dashboard/accounts/premium-drawer.vue'
import StopPremiumModal from '@/components/dashboard/accounts/stop-premium-modal.vue'
import AccountStatusBadge from '@/components/dashboard/accounts/status-badge.vue'
import AccountsBulkActionsMenu from '@/components/dashboard/accounts/bulk-actions-menu.vue'

import { useAccounts } from '@/composables/use-accounts'
import { useTitle, useLocalStorage } from '@vueuse/core'

import type { TableColumn } from '@nuxt/ui'
import { ref, onMounted, onUnmounted, onActivated, onDeactivated, h, resolveComponent, computed, watch, watchEffect } from 'vue'

import { useTableSelection } from '@/composables/table/use-selection'
import type { AccountOut, AccountStateOut } from '@/types/openapi'
import type { Column, SortingFn, VisibilityState } from '@tanstack/vue-table'
import { upperFirst } from 'scule'

const title = 'Аккаунты'
useTitle(title)
const { get, state, accounts, loading } = useAccounts()
const toast = useToast()

// "Отлежка" (в часах): 0 = отключена.
// Если захочешь конфиг с бэка/ENV - вынесем, но пока держим тут.
const HOLD_HOURS = 0
const HOLD_MS = HOLD_HOURS * 60 * 60 * 1000

const NOW_TICK_MS = 30_000
const nowMs = ref(Date.now())
// Дергаем UTable через attrs, т.к. при неизменных props она может не апдейтиться,
// а слоты завязаны на nowMs (отлежка).
const holdTick = computed(() => Math.floor(nowMs.value / NOW_TICK_MS))
let lastNowUpdateMs = 0
function maybeUpdateNowMs () {
  if (HOLD_MS <= 0) return
  const t = Date.now()
  if (t - lastNowUpdateMs >= NOW_TICK_MS) {
    lastNowUpdateMs = t
    nowMs.value = t
  }
}

function toMs (value: string | Date | null | undefined): number | null {
  if (!value) return null
  const d = value instanceof Date ? value : new Date(value)
  const t = d.getTime()
  return Number.isNaN(t) ? null : t
}

function holdUntilMs (account: AccountOut): number | null {
  if (HOLD_MS <= 0) return null
  const created = toMs(account.createdAt)
  if (created === null) return null
  return created + HOLD_MS
}

function isInHold (account: AccountOut): boolean {
  const until = holdUntilMs(account)
  if (until === null) return false
  return nowMs.value < until
}

function holdUntilLabel (account: AccountOut): string | null {
  const until = holdUntilMs(account)
  if (until === null) return null
  return formatDateTimeDDMMYY_HHMM(until)
}

function holdRemainingLabel (account: AccountOut): string | null {
  const until = holdUntilMs(account)
  if (until === null) return null
  const remainingMs = until - nowMs.value
  if (remainingMs <= 0) return null
  return formatRemainingHHMM(remainingMs)
}

// Дорогие вычисления по всему списку (filter по accounts) лучше не триггерить
// на каждый state-poll, т.к. мы каждые 5s меняем поля `busy/status/premium` у элементов.
const accountsTotal = computed(() => accounts.value.length)
const accountsWithoutProxy = ref(0)
watch(accounts, (list) => {
  accountsWithoutProxy.value = list.filter(a => !a.proxy).length
}, { immediate: true })

const accountsCountLabel = computed(() => {
  const n = accountsTotal.value
  const m = accountsWithoutProxy.value
  return m > 0 ? `Аккаунтов: ${n} (без прокси: ${m})` : `Аккаунтов: ${n}`
})

const navbarUi = { right: 'gap-3' } as const
const dropdownContent = { align: 'end' } as const
const tableUi = {
  base: 'table-fixed border-separate border-spacing-0',
  thead: '[&>tr]:bg-elevated/50 [&>tr]:after:content-none',
  tbody: '[&>tr]:last:[&>td]:border-b-0',
  th: 'py-2 first:rounded-l-lg last:rounded-r-lg border-y border-default first:border-l last:border-r',
  td: 'border-b border-default',
} as const

// Drawer управление
const drawerOpen = ref(false)
const premiumDrawerOpen = ref(false)

const selectedAccountId = ref<number | null>(null)

function openDrawer (account: AccountOut) {
  if (isInHold(account)) {
    const until = holdUntilLabel(account)
    toast.add({
      title: until ? `Отлежка до ${until}` : 'Аккаунт на отлежке',
      color: 'warning',
    })
    return
  }
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
  if (isInHold(account)) {
    const until = holdUntilLabel(account)
    toast.add({
      title: until ? `Отлежка до ${until}` : 'Аккаунт на отлежке',
      color: 'warning',
    })
    return
  }
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
const COLUMN_VISIBILITY_STORAGE_KEY = 'dashboard.accounts.columnVisibility'
const HIDEABLE_COLUMN_IDS = ['premiumedAt', 'outDailyLimit', 'dialogsCount', 'createdAt'] as const
type HideableColumnId = (typeof HIDEABLE_COLUMN_IDS)[number]

const columnVisibility = useLocalStorage<VisibilityState>(COLUMN_VISIBILITY_STORAGE_KEY, {})

// Normalize stored value:
// - keep only hideable columns
// - keep only `false` entries (hidden); visible defaults to `true` when absent
watchEffect(() => {
  const current = columnVisibility.value ?? {}
  const next: VisibilityState = {}

  for (const id of HIDEABLE_COLUMN_IDS) {
    if (current[id] === false) {
      next[id] = false
    }
  }

  const currentKeys = Object.keys(current)
  const nextKeys = Object.keys(next)
  if (currentKeys.length !== nextKeys.length) {
    columnVisibility.value = next
    return
  }
  for (const k of nextKeys) {
    if (current[k] !== next[k]) {
      columnVisibility.value = next
      return
    }
  }
})
const UIcon = resolveComponent('UIcon')
const { tableApi, selectedIds, selectionColumn } = useTableSelection<AccountOut>('table', 'id', {
  isSelectable: (row) => !row.busy && !isInHold(row),
  renderNonSelectable: (row) => {
    const hold = isInHold(row)
    const title = hold ? `Отлежка до ${holdUntilLabel(row) ?? ''}`.trim() : 'Аккаунт в работе'
    return h('div', { class: 'flex items-center justify-center w-full' }, [
      h(UIcon, {
        name: hold ? 'i-lucide-clock' : 'i-lucide-loader-circle',
        class: hold ? 'h-4 w-4 text-muted' : 'h-4 w-4 animate-spin text-warning',
        title,
        'aria-label': title,
      }),
    ])
  },
})

const STATE_POLL_INTERVAL = 5000
const stateSyncInFlight = ref(false)
let statePollTimer: ReturnType<typeof setInterval> | null = null

function cleanupNonSelectableSelection () {
  if (!tableApi.value) return
  tableApi.value.getSelectedRowModel().rows.forEach((row) => {
    if (row.original.busy || isInHold(row.original)) {
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
    cleanupNonSelectableSelection()
  }
}

async function syncState () {
  if (stateSyncInFlight.value || !accounts.value.length) return

  stateSyncInFlight.value = true
  // Используем state poll как heartbeat для отлежки (не чаще NOW_TICK_MS).
  maybeUpdateNowMs()
  try {
    const states = await state()
    applyStateUpdates(states)
  } catch (e) {
    console.error('accounts state sync failed', e)
  } finally {
    // Даже если state упал, пусть UI продолжает "тикать" и отлежка снимется вовремя.
    maybeUpdateNowMs()
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
  maybeUpdateNowMs()
  void syncState()
  startStatePolling()
})

onActivated(() => {
  startStatePolling()
  maybeUpdateNowMs()
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

const hideableColumnLabels: Record<HideableColumnId, string> = {
  premiumedAt: 'Прем. куплен',
  outDailyLimit: 'Лимит',
  dialogsCount: 'Диалоги',
  createdAt: 'Создан',
}

const columnVisibilityItems = computed(() => {
  const api = tableApi.value
  if (!api) return []

  return api
    .getAllColumns()
    .filter((column) => column.getCanHide())
    .map((column) => ({
      label: hideableColumnLabels[column.id as HideableColumnId] ?? upperFirst(column.id),
      type: 'checkbox' as const,
      checked: column.getIsVisible(),
      onUpdateChecked (checked: boolean) {
        api.getColumn(column.id)?.toggleVisibility(!!checked)
      },
      onSelect (e: Event) {
        e.preventDefault()
      },
    }))
})

const limitSortingFn: SortingFn<AccountOut> = (rowA, rowB) => {
  const getLimit = (row: AccountOut) =>
    row.isDynamicLimit ? row.dynamicDailyLimit : row.outDailyLimit

  const valueA = getLimit(rowA.original) ?? 0  // null/undefined -> 0
  const valueB = getLimit(rowB.original) ?? 0

  return valueA - valueB
}

const projectSortingFn: SortingFn<AccountOut> = (rowA, rowB) => {
  const a = (rowA.original.project?.name ?? '').toLowerCase()
  const b = (rowB.original.project?.name ?? '').toLowerCase()

  // "не назначен" отправляем в конец
  if (!a && !b) return 0
  if (!a) return 1
  if (!b) return -1

  return a.localeCompare(b, 'ru')
}

const proxySortingFn: SortingFn<AccountOut> = (rowA, rowB) => {
  const a = (rowA.original.proxy ?? '').toLowerCase()
  const b = (rowB.original.proxy ?? '').toLowerCase()

  // null/"" отправляем в конец
  if (!a && !b) return 0
  if (!a) return 1
  if (!b) return -1

  return a.localeCompare(b, 'ru')
}

const columns: TableColumn<AccountOut>[] = [
  { ...selectionColumn(), enableHiding: false },
  {
    accessorKey: 'id',
    header: "ID",
    enableHiding: false

  },
  {
    accessorKey: 'status',
    header: ({ column }) => getHeader(column, 'Статус'),
    ...columnCentered,
    enableHiding: false,
  },
  {
    accessorKey: 'proxy',
    header: ({ column }) => getHeader(column, 'Прокси'),
    sortingFn: proxySortingFn,
    ...columnCentered,
    enableHiding: false,
  },
  {
    accessorKey: 'project',
    header: ({ column }) => getHeader(column, 'Проект'),
    sortingFn: projectSortingFn,
    meta: {
      class: {
        th: 'w-[200px] max-w-[200px]',
        td: 'w-[200px] max-w-[200px] whitespace-normal break-words [overflow-wrap:anywhere] hyphens-auto',
      },
    },
    enableHiding: false,

  },
  {
    accessorKey: 'phone',
    header: 'Телефон',
    enableHiding: false,
  },
  {
    accessorKey: 'country',
    header: ({ column }) => getHeader(column, 'Страна'),
    enableHiding: false,
  },
  {
    accessorKey: 'name',
    header: 'Имя',
    meta: {
      class: {
        th: 'text-center',
      },
    },
    enableHiding: false,
  },
  {
    accessorKey: 'premium',

    header: ({ column }) => getHeader(column, 'Премиум'),
    ...columnCentered,
    enableHiding: false,
  },
  {
    accessorKey: 'premiumedAt',
    header: 'Прем. куплен',
    cell: ({ row }) => {
      if (row.original.premiumedAt) {
        return formatDateDDMMYY(row.original.premiumedAt)
      } else {
        return "---"
      }

    },
    ...columnCentered,
    enableHiding: true,
  },
  {
    accessorKey: 'outDailyLimit',
    header: ({ column }) => getHeader(column, 'Лимит'),
    ...columnCentered,
    sortingFn: limitSortingFn,
    enableHiding: true,

  },
  {
    accessorKey: 'dialogsCount',
    header: ({ column }) => getHeader(column, '💬'),
    ...columnCentered,
    enableHiding: true,

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
    cell: ({ row }) => formatDateDDMMYY(row.original.createdAt),
    enableHiding: true,
  },
]

const dateDDMMYY = new Intl.DateTimeFormat('ru-RU', {
  day: '2-digit',
  month: '2-digit',
  year: '2-digit',
})

function formatDateDDMMYY (value: string | Date | null | undefined): string {
  if (!value) return '---'
  const d = value instanceof Date ? value : new Date(value)
  // Guard against invalid dates
  if (Number.isNaN(d.getTime())) return '---'
  return dateDDMMYY.format(d)
}

function formatDateTimeDDMMYY_HHMM (value: number | string | Date | null | undefined): string {
  const ms =
    typeof value === 'number'
      ? value
      : value instanceof Date
        ? value.getTime()
        : typeof value === 'string'
          ? new Date(value).getTime()
          : NaN

  if (!Number.isFinite(ms)) return '---'
  const d = new Date(ms)
  const hh = String(d.getHours()).padStart(2, '0')
  const mm = String(d.getMinutes()).padStart(2, '0')
  return `${dateDDMMYY.format(d)} ${hh}:${mm}`
}

function formatRemainingHHMM (remainingMs: number): string {
  const totalMinutes = Math.max(0, Math.floor(remainingMs / 60_000))
  const hours = Math.floor(totalMinutes / 60)
  const minutes = totalMinutes % 60
  return `${String(hours).padStart(2, '0')}:${String(minutes).padStart(2, '0')}`
}
</script>

<style scoped>
.project-cell-text {
  white-space: normal;
  overflow-wrap: anywhere;
  word-break: normal;
  hyphens: auto;
}
</style>
