<template>
  <UForm ref="form" :schema="balanceSchema" :state="state" @submit="onSubmit">
    <UFormField label="Username" name="username" class="mb-4">
      <UInput
        v-model="state.username"
        size="md"
        class="w-full"
        :disabled="loading"
        icon="i-lucide-at-sign"
      />
    </UFormField>

    <UFormField label="Сумма" name="days" class="mb-4">
      <UInput
        v-model.number="state.amount"
        type="number"
        size="md"
        class="w-full"
        :min="1"
        :disabled="loading"
      >
        <template #trailing>
          <span class="text-gray-500 dark:text-gray-400">₽</span>
        </template>
      </UInput>
    </UFormField>

    <UButton type="submit" :loading="loading" :disabled="loading">Начислить баланс</UButton>

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
  </UForm>
</template>

<script setup lang="ts">
import { balanceSchema, type BalanceSchema } from '@/schemas/admin'
import type { BalanceIn, BalanceOut } from '@/types/openapi'
import type { FormSubmitEvent } from '@nuxt/ui'
import { useTitle } from '@vueuse/core'
import { reactive, ref } from 'vue'
import { useAdmin } from '@/composables/use-admin'

const title = 'Админка - Баланс>'

useTitle(title)

const { addBalance, loading, error } = useAdmin()

const state = reactive({
  username: '',
  amount: 0,
})

const response = ref<BalanceOut | null>(null)

const onSubmit = async (event: FormSubmitEvent<BalanceSchema>) => {
  response.value = null // Сбрасываем предыдущий результат

  const data = event.data satisfies BalanceIn
  const result = await addBalance(data)

  if (result) {
    response.value = result

    // Если успешно, очищаем форму
    if (result.status === 'success') {
      state.username = ''
      state.amount = 0
    }
  }
}
</script>
