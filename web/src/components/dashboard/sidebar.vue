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
      <UNavigationMenu
        :collapsed="collapsed"
        :items="links"
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
import { ref } from 'vue'

const open = ref(false)

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
] satisfies NavigationMenuItem[]
</script>
