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
import AppUserMenu from './AppUserMenu.vue'
import type { NavigationMenuItem } from '@nuxt/ui'
import Logo from '@/components/shared/Logo.vue'
import { ref } from 'vue'

const open = ref(false)

const links = [
  {
    label: 'Главная',
    icon: 'i-lucide-house',
    to: '/app',
    exact: true,
    onSelect: () => (open.value = false),
  },
  {
    label: 'Прокси',
    icon: 'i-lucide-server',
    to: '/app/proxies',
    onSelect: () => (open.value = false),
  },
  {
    label: 'Аккаунты',
    icon: 'i-lucide-users',
    to: '/app/accounts',
    onSelect: () => (open.value = false),
  },
  {
    label: 'Проекты',
    to: '/app/projects',
    icon: 'lucide:file-chart-column-increasing',
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
