<template>
  <UDashboardPanel id="settings">
    <template #header>
      <UDashboardNavbar :title="title" :ui="{ right: 'gap-3' }">
        <template #leading>
          <UDashboardSidebarCollapse />
        </template>
      </UDashboardNavbar>
    </template>
    <template #body>
      <div class="min-w-[800px] max-w-4xl mx-auto">
        <UTabs :items="tabs" variant="link" :ui="{ trigger: 'grow' }" class="gap-4">
          <template #aiModel>
            <AiModelsTab />
          </template>
          <template #partners>
            <PartnersTab />
          </template>
        </UTabs>
      </div>
    </template>
  </UDashboardPanel>
</template>
<script setup lang="ts">
import { useTitle } from '@vueuse/core'
import type { TabsItem } from '@nuxt/ui'
import AiModelsTab from '@/components/dashboard/settings/ai-models-tab.vue'
import PartnersTab from '@/components/dashboard/settings/partners-tab.vue'

const title = 'Настройки'
useTitle(title)

const tabs = [
  { label: 'AI Модель', icon: 'i-heroicons-cpu-chip', slot: 'aiModel' as const },
  { label: 'Партнерка', icon: 'carbon:partnership', slot: 'partners' as const },
] satisfies TabsItem[]

</script>
