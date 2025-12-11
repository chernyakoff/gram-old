<template>
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

      <UButton type="submit" :loading="loading" :disabled="loading">Вход</UButton>

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

<script setup lang="ts">
import { licenseSchema, type LicenseSchema } from '@/schemas/admin'
import type { LicenseIn, LicenseOut } from '@/types/openapi'
import type { FormSubmitEvent } from '@nuxt/ui'
import { useTitle } from '@vueuse/core'
import { reactive, ref } from 'vue'
import { useAdmin } from '@/composables/use-admin'

const title = 'Админка'

useTitle(title)

const { impersonate, loading, error } = useAdmin()

const state = reactive({
  username: '',
})

const response = ref<LicenseOut | null>(null)

const onSubmit = async (event: FormSubmitEvent<LicenseSchema>) => {
  response.value = null // Сбрасываем предыдущий результат

  const data = event.data satisfies LicenseIn
  const { access } = await impersonate(data)
}
</script>
