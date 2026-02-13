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

const links: NavigationMenuItem[] = [
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
    label: 'Календарь',
    to: '/app/calendar',
    icon: 'bxs-calendar',
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
]

const balanceRub = computed(() => {
  const balance = user.value?.balance ?? 0
  return new Intl.NumberFormat('ru-RU', {
    style: 'currency',
    currency: 'RUB',
    minimumFractionDigits: 2,
  }).format(balance / 100)
})

const filteredLinks = computed(() => {
  const isImpersonated = user.value?.impersonated === true

  return links
    .filter((link) => {
      const to = link.to
      if (typeof to === 'string' && to.includes('admin')) {
        // Client-side hiding isn't security; backend must still enforce admin access.
        // Show admin entry to real admins and to admins currently impersonating a user.
        return user.value?.role === 'ADMIN' || isImpersonated
      }
      return true
    })
    .map((link) => {
      if (link.to === '/app/admin' && isImpersonated) {
        return {
          ...link,
          // Visual warning: you're in impersonation mode.
          class: ['text-red-600 dark:text-red-400', link.class],
        }
      }
      return link
    })
})
</script>
