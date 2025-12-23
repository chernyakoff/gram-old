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
      <div class="min-w-[800px] max-w-4xl mx-auto">
        <UTabs :items="tabs" variant="link" :ui="{ trigger: 'grow' }" class="gap-4">
          <template #license><AdminLicenseForm /></template>
          <template #impersonate><AdminImpersonateForm /></template>
          <template #balance><AdminBalanceForm /></template>
          <template #prompts>
            <UTabs :items="promptTabs" variant="link" :ui="{ trigger: 'grow' }" class="gap-4">
              <template #system>
                <AdminPromptForm label="Системный" path="prompt.system" />
              </template>
              <template #generator>
                <AdminPromptForm label="Генератор" path="prompt.generator" />
              </template>
              <template #findStatus>
                <AdminPromptForm label="Поиск статуса" path="prompt.findStatus" />
              </template>
            </UTabs>
          </template>
        </UTabs>
      </div>
    </template>
  </UDashboardPanel>
</template>

<script setup lang="ts">
import type { TabsItem } from '@nuxt/ui'
import { useTitle } from '@vueuse/core'
import AdminLicenseForm from '@/components/dashboard/admin/license-form.vue'
import AdminBalanceForm from '@/components/dashboard/admin/balance-form.vue'
import AdminImpersonateForm from '@/components/dashboard/admin/impersonate-form.vue'
import AdminPromptForm from '@/components/dashboard/admin/prompt-form.vue'

const title = 'Админка'

const tabs = [
  { label: 'Лицензии', icon: 'bx:badge-check', slot: 'license' as const },
  { label: 'Баланс', icon: 'bx:user', slot: 'balance' as const },
  { label: 'Юзер-логин', icon: 'bx:user', slot: 'impersonate' as const },
  { label: 'Промпты', icon: 'bx:brain', slot: 'prompts' as const },
] satisfies TabsItem[]

const promptTabs = [
  { label: 'Системный', icon: 'bx:cog', slot: 'system' as const },
  { label: 'Генератор', icon: 'bx:bxs-edit-alt', slot: 'generator' as const },
  { label: 'Поиск статуса', icon: 'bx:bxs-edit-alt', slot: 'findStatus' as const },
] satisfies TabsItem[]

useTitle(title)
</script>
