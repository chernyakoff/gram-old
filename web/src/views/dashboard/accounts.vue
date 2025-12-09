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
        :ui="{
          base: 'table-fixed border-separate border-spacing-0',
          thead: '[&>tr]:bg-elevated/50 [&>tr]:after:content-none',
          tbody: '[&>tr]:last:[&>td]:border-b-0',
          th: 'py-2 first:rounded-l-lg last:rounded-r-lg border-y border-default first:border-l last:border-r',
          td: 'border-b border-default',
        }"
      >
        <template #status-cell="{ row }">
          <AccountStatusBadge :account="row.original" />
        </template>
        <template #project-cell="{ row }">
          {{ row.original.project?.name ?? 'не назначен' }}
        </template>
        <template #premium-cell="{ row }">
          <div class="flex items-center gap-1 justify-center">
            <template v-if="!row.original.premium">
              <button class="flex items-center gap-1" @click="openPremiumDrawer(row.original)">
                <UIcon name="bx:cart" class="h-6 w-6" />
              </button>
            </template>

            <template v-else-if="row.original.premium && !row.original.premiumStopped">
              <button class="flex items-center gap-1" @click="openPremiumDrawer(row.original)">
                <UIcon name="bxs:star" class="h-6 w-6 text-yellow-400" />
              </button>
            </template>
            <template v-else>
              <UIcon name="bxs:star" class="h-6 w-6 text-gray-400" />
            </template>
          </div>
        </template>
        <template #name-cell="{ row }">
          <div class="flex items-center gap-3" @click="openDrawer(row.original)">
            <UButton
              v-if="row.original.photos.length"
              class="rounded-full"
              color="neutral"
              variant="link"
            >
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
    :accountId="selectedAccountId"
    :key="selectedAccountId"
    @completed="refresh"
  />
  <PremiumDrawer
    v-if="selectedAccountId !== null"
    v-model:open="premiumDrawerOpen"
    :accountId="selectedAccountId"
    :key="selectedAccountId"
    @completed="refresh"
  />
</template>
<script setup lang="ts">
import DeleteAccountsModal from '@/components/dashboard/accounts/delete-modal.vue'
import AddAccountsModal from '@/components/dashboard/accounts/add-modal.vue'
import BindProjectModal from '@/components/dashboard/accounts/project-modal.vue'
import SetLimitmodal from '@/components/dashboard/accounts/limit-modal.vue'
import CheckModal from '@/components/dashboard/accounts/check-modal.vue'
import AccountDrawer from '@/components/dashboard/accounts/drawer.vue'
import PremiumDrawer from '@/components/dashboard/accounts/premium-drawer.vue'
import AccountStatusBadge from '@/components/dashboard/accounts/status-badge.vue'

import { useAccounts } from '@/composables/use-accounts'
import { useTitle, useDateFormat } from '@vueuse/core'

import type { TableColumn } from '@nuxt/ui'
import { ref, onMounted } from 'vue'

import { useTableSelection } from '@/composables/table/use-selection'
import type { AccountOut } from '@/types/openapi'

const title = 'Аккаунты'
useTitle(title)
const { get, accounts, loading } = useAccounts()
const toast = useToast()
onMounted(() => get())

// Drawer управление
const drawerOpen = ref(false)
const premiumDrawerOpen = ref(false)

const selectedAccountId = ref<number | null>(null)

function openDrawer(account: AccountOut) {
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

function openPremiumDrawer(account: AccountOut) {
  selectedAccountId.value = account.id
  premiumDrawerOpen.value = true
}

const refresh = () => {
  tableApi.value?.setRowSelection({})
  get()
}

const columnFilters = ref([{ id: 'phone', value: '' }])
const columnVisibility = ref()
const { tableApi, selectedIds, selectionColumn } = useTableSelection<AccountOut>('table', 'id', {
  isSelectable: (row) => !row.busy,
})

const columnCentered = {
  meta: {
    class: {
      th: 'text-center',
      td: 'text-center',
    },
  },
}

const columns: TableColumn<AccountOut>[] = [
  selectionColumn(),
  {
    accessorKey: 'id',
    header: 'ID',
  },
  {
    accessorKey: 'status',
    header: 'Статус',
    ...columnCentered,
  },
  {
    accessorKey: 'project',
    header: 'Проект',
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
    accessorKey: 'premium',
    header: 'Премиум',
    ...columnCentered,
  },
  {
    accessorKey: 'outDailyLimit',
    header: 'Лимит',
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
    header: 'Загружен',
    cell: ({ row }) => useDateFormat(row.original.createdAt, 'DD.MM.YY').value,
  },
]
</script>
