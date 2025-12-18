<template>
  <UDashboardPanel id="settings">
    <template #header>
      <UDashboardNavbar :title="title" :ui="{ right: 'gap-3' }">
        <template #leading>
          <UDashboardSidebarCollapse />
        </template>
        <template #right>
          <UButton size="lg" type="submit" label="Сохранить" color="primary" @click="doSubmit" />
        </template>
      </UDashboardNavbar>
    </template>
    <template #body>
      <UForm ref="form" :schema="settingsSchema" :state="state" @submit="onSubmit">
        <div class="min-w-[800px] max-w-4xl mx-auto">
          <UTabs :items="tabs" variant="link" :ui="{ trigger: 'grow' }" class="gap-4">
            <template #proxyapi>
              <UFormField label="API Ключ" name="proxyApi.apiKey" class="mb-4">
                <UInput
                  v-model="state.proxyApi.apiKey"
                  size="md"
                  class="w-1/2"
                  :disabled="loading"
                />

                <template #hint>
                  <span v-if="state.proxyApi.error" class="flex items-center gap-1 text-red-600">
                    {{ state.proxyApi.error }}
                    <UPopover
                      v-if="state.proxyApi.error?.includes('Включите доступ к балансу')"
                      :popper="{ placement: 'right' }"
                      mode="hover"
                    >
                      <UButton
                        icon="bx:bxs-info-circle"
                        color="neutral"
                        variant="link"
                        size="md"
                        :padded="false"
                      />
                      <template #content>
                        <div class="p-2">
                          <img
                            src="@/assets/proxyapi-balance-access.png"
                            alt="Как включить доступ к балансу"
                            class="max-w-2xl rounded border"
                          />
                        </div>
                      </template>
                    </UPopover>
                  </span>

                  <span
                    v-else-if="typeof state.proxyApi.balance === 'number'"
                    class="text-green-600"
                  >
                    Баланс: {{ state.proxyApi.balance.toLocaleString() }}
                  </span>
                </template>
              </UFormField>
            </template>
          </UTabs>
        </div>
      </UForm>
    </template>
  </UDashboardPanel>
</template>
<script setup lang="ts">
import { useTitle } from '@vueuse/core'
import type { FormSubmitEvent, TabsItem } from '@nuxt/ui'
import { useSettings } from '@/composables/use-settings'
import { onMounted, reactive } from 'vue'
import { type SettingsIn } from '@/types/openapi'
import { settingsSchema, type SettingsSchema } from '@/schemas/settings'
import { useTemplateRef } from 'vue'

const { get, save, loading } = useSettings()

const title = 'Настройки'
useTitle(title)

const tabs = [
  { label: 'ProxyApi', icon: 'bx:brain', slot: 'proxyapi' as const },
] satisfies TabsItem[]

const form = useTemplateRef('form')

const doSubmit = async () => {
  await form.value?.submit()
}

const state = reactive<
  SettingsIn & { proxyApi: { apiKey: string; error?: string; balance?: number } }
>({
  proxyApi: {
    apiKey: '',
    error: undefined,
    balance: undefined,
  },
})

onMounted(async () => {
  const settings = await get()
  // proxy_api приходит как { api_key, balance, error }
  Object.assign(state, {
    proxyApi: {
      apiKey: settings.proxyApi?.apiKey || '',
      balance: settings.proxyApi?.balance,
      error: settings.proxyApi?.error,
    },
  })
})

const onSubmit = async (event: FormSubmitEvent<SettingsSchema>) => {
  const settings = await save(event.data)
  Object.assign(state, {
    proxyApi: {
      apiKey: settings.proxyApi?.apiKey || '',
      balance: settings.proxyApi?.balance,
      error: settings.proxyApi?.error,
    },
  })
}
</script>
