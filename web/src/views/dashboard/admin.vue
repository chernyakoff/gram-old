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
      <UForm ref="form" :schema="licenseSchema" :state="state" @submit="onSubmit">
        <div class="min-w-[800px] max-w-4xl mx-auto">
          <UFormField label="Username" name="username" class="mb-4">
            <UInput
              v-model="state.username"
              size="md"
              class="w-full"
              :disabled="loading"
              icon="i-lucide-at-sign"
            />
          </UFormField>

          <UFormField label="Кол-во дней" name="days" class="mb-4">
            <UInput
              v-model.number="state.days"
              type="number"
              size="md"
              class="w-full"
              :min="1"
              :disabled="loading"
            />
          </UFormField>

          <UButton type="submit" :loading="loading" :disabled="loading">Выписать лицензию</UButton>

          <!-- Вывод результата -->
          <div v-if="response" class="mt-6">
            <UAlert
              :color="response.status === 'success' ? 'success' : 'error'"
              :variant="response.status === 'success' ? 'soft' : 'solid'"
              :title="response.status === 'success' ? 'Успешно' : 'Ошибка'"
              :description="response.message"
              :icon="
                response.status === 'success'
                  ? 'i-heroicons-check-circle'
                  : 'i-heroicons-exclamation-circle'
              "
            />
          </div>

          <!-- Общая ошибка -->
          <div v-if="error && !response" class="mt-6">
            <UAlert
              color="error"
              variant="solid"
              title="Ошибка"
              :description="error"
              icon="i-heroicons-exclamation-triangle"
            />
          </div>
        </div>
      </UForm>
    </template>
  </UDashboardPanel>
</template>

<script setup lang="ts">
import { licenseSchema, type LicenseSchema } from '@/schemas/admin'
import type { LicenseIn, LicenseOut } from '@/types/openapi'
import type { FormSubmitEvent } from '@nuxt/ui'
import { useTitle } from '@vueuse/core'
import { reactive, ref } from 'vue'
import { useAdmin } from '@/composables/use-admin'

const title = 'Админка'

useTitle(title)

const { license, loading, error } = useAdmin()

const state = reactive({
  username: '',
  days: 30,
})

const response = ref<LicenseOut | null>(null)

const onSubmit = async (event: FormSubmitEvent<LicenseSchema>) => {
  response.value = null // Сбрасываем предыдущий результат

  const data = event.data satisfies LicenseIn
  const result = await license(data)

  if (result) {
    response.value = result

    // Если успешно, очищаем форму
    if (result.status === 'success') {
      state.username = ''
      state.days = 30
    }
  }
}
</script>
