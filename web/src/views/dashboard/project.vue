<template>
  <UDashboardPanel>
    <template #header>
      <UDashboardNavbar :title="title" :ui="{ right: 'gap-3' }">
        <template #leading>
          <UDashboardSidebarCollapse />
        </template>
        <template #right>
          <UButton
            size="lg"
            label="Назад"
            variant="outline"
            color="neutral"
            @click="$router.back()"
          />
        </template>
      </UDashboardNavbar>
    </template>
    <template #body>
      <UTabs :items="tabs" variant="link" :ui="{ trigger: 'grow' }" class="gap-4">
        <template #settings><ProjectSettingsTab :projectId="projectId" /></template>
      </UTabs>
    </template>
  </UDashboardPanel>
</template>
<script setup lang="ts">
import { useTitle } from '@vueuse/core'
import type { TabsItem } from '@nuxt/ui'
import ProjectSettingsTab from '@/components/dashboard/project/settings-tab.vue'

const title = 'Редактирование проекта'
useTitle(title)

const props = defineProps<{ id: string }>()
const projectId = Number(props.id)

const tabs = [
  { label: 'Настройки', icon: 'bx:cog', slot: 'settings' as const },
  { label: 'Бриф', icon: 'bx:user', slot: 'brief' as const },
  { label: 'Промпт', icon: 'bx:brain', slot: 'prompt' as const },
  { label: 'Файлы', icon: 'bx:brain', slot: 'files' as const },
  { label: 'База знаний', icon: 'bx:brain', slot: 'knowledge' as const },
] satisfies TabsItem[]
</script>
