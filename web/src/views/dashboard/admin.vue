<template>
  <UDashboardPanel id="admin">
    <template #header>
      <UDashboardNavbar :title="title" :ui="{ right: 'gap-3' }">
        <template #leading>
          <UDashboardSidebarCollapse />
        </template>
      </UDashboardNavbar>
    </template>
    <template #body>
      <UTabs :items="tabs" variant="link" :ui="{ trigger: 'grow' }" class="gap-4 w-full">
        <template #license><AdminLicenseForm /></template>
      </UTabs>
    </template>
  </UDashboardPanel>
</template>

<script setup lang="ts">
import type { TabsItem } from '@nuxt/ui'
import { useTitle } from '@vueuse/core'
import AdminLicenseForm from '@/components/dashboard/admin/license-form.vue'

const title = 'Админка'

const tabs = [
  { label: 'Лицензии', icon: 'i-lucide-list', slot: 'license' as const },
  { label: 'Юзер-логин', icon: 'i-lucide-image', slot: 'impersonate' as const },
] satisfies TabsItem[]

useTitle(title)
</script>
