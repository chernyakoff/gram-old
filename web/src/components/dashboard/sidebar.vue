<template>
  <UDashboardSidebar
    id="default"
    v-model:open="open"
    collapsible
    resizable
    class="bg-elevated/25"
    :ui="{ footer: 'lg:border-t lg:border-default' }"
  >
    <template #header="{ collapsed }">
      <Logo :collapsed="collapsed" />
    </template>
    <template #default="{ collapsed }">
      <div
        class="py-3 mb-2 text-sm flex items-center"
        :class="collapsed ? 'justify-center' : 'justify-between'"
      >
        <span v-if="!collapsed" class="text-muted">Баланс</span>
        <span class="font-semibold tabular-nums">
          {{ balanceRub }}
        </span>
      </div>
      <UNavigationMenu
        :collapsed="collapsed"
        :items="filteredLinks"
        orientation="vertical"
        tooltip
        popover
      />
    </template>
    <template #footer="{ collapsed }">
      <AppUserMenu :collapsed="collapsed" />
    </template>
  </UDashboardSidebar>
</template>
<script setup lang="ts">
import AppUserMenu from '@/components/dashboard/user-menu.vue'
import type { NavigationMenuItem } from '@nuxt/ui'
import Logo from '@/components/shared/logo.vue'
import { computed, ref } from 'vue'
import { useAuth } from '@/composables/use-auth'

const open = ref(false)

const { user } = useAuth()

const links = [
  {
    label: 'Дашборд',
    icon: 'bx-bxs-bar-chart-alt-2',
    to: '/app',
    exact: true,
    onSelect: () => (open.value = false),
  },
  {
    label: 'Прокси',
    icon: 'bx-server',
    to: '/app/proxies',
    onSelect: () => (open.value = false),
  },
  {
    label: 'Аккаунты',
    icon: 'bx-spreadsheet',
    to: '/app/accounts',
    onSelect: () => (open.value = false),
  },
  {
    label: 'Проекты',
    to: '/app/projects',
    icon: 'bx-network-chart',
    onSelect: () => (open.value = false),
  },
  {
    label: 'Рассылки',
    to: '/app/mailings',
    icon: 'bx-mail-send',
    onSelect: () => (open.value = false),
  },
  {
    label: 'Диалоги',
    to: '/app/dialogs',
    icon: 'bx-chat',
    onSelect: () => (open.value = false),
  },
  {
    label: 'Задачи',
    to: '/app/jobs',
    icon: 'i-lucide-logs',
    onSelect: () => (open.value = false),
  },
  {
    label: 'Настройки',
    to: '/app/settings',
    icon: 'bx:cog',
    onSelect: () => (open.value = false),
  },
  {
    label: 'Админка',
    to: '/app/admin',
    icon: 'bx:bxl-gitlab',
    onSelect: () => (open.value = false),
  },
] satisfies NavigationMenuItem[]

const balanceRub = computed(() => {
  const balance = user.value?.balance ?? 0
  return new Intl.NumberFormat('ru-RU', {
    style: 'currency',
    currency: 'RUB',
    minimumFractionDigits: 2,
  }).format(balance / 100)
})

const filteredLinks = computed(() => {
  return links.filter((link) => {
    if (link.to?.includes('admin')) {
      return user.value?.role === 'ADMIN'
    }
    return true
  })
})
</script>
