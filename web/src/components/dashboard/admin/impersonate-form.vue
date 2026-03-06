<!-- AdminImpersonate.vue -->
<template>
  <UForm ref="form" :schema="impersonateSchema" :state="state" @submit="onSubmit">
    <UFormField label="Username" name="username" class="mb-4">
      <UInput
        v-model="state.username"
        size="md"
        class="w-full"
        :disabled="loading"
        icon="i-lucide-at-sign"
      />
    </UFormField>

    <UButton type="submit" :loading="loading" :disabled="loading">Войти как пользователь</UButton>

    <!-- Успешный результат -->
    <div v-if="impersonateSuccess" class="mt-6">
      <UAlert
        color="success"
        variant="soft"
        title="Успешно"
        description="Вход выполнен. Перенаправление..."
        icon="i-heroicons-check-circle"
      />
    </div>

    <!-- Ошибка -->
    <div v-if="impersonateError" class="mt-6">
      <UAlert
        color="error"
        variant="solid"
        title="Ошибка"
        description="Пользователь не найден"
        icon="i-heroicons-exclamation-triangle"
      />
    </div>
  </UForm>
</template>

<script setup lang="ts">
import { impersonateSchema, type ImpersonateSchema } from '@/schemas/admin'
import type { ImpersonateIn } from '@/types/openapi'
import type { FormSubmitEvent } from '@nuxt/ui'
import { useTitle } from '@vueuse/core'
import { reactive, ref } from 'vue'
import { useAuth } from '@/composables/use-auth'

const title = 'Админка - Имперсонация'

useTitle(title)

const { impersonate } = useAuth()

const state = reactive({
  username: '',
})

const loading = ref(false)
const impersonateSuccess = ref(false)
const impersonateError = ref(false)

const onSubmit = async (event: FormSubmitEvent<ImpersonateSchema>) => {
  impersonateSuccess.value = false
  impersonateError.value = false
  loading.value = true

  try {
    const data = event.data satisfies ImpersonateIn
    await impersonate(data)

    impersonateSuccess.value = true
    // Редирект произойдёт автоматически через watch в useAuth
  } catch (e) {
    impersonateError.value = true
    console.error('Impersonate error:', e)
  } finally {
    loading.value = false
  }
}
</script>
