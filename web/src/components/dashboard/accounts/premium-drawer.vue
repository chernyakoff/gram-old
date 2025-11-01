<template>
  <UDrawer
    direction="right"
    class="w-160"
    :handle="false"
    v-model:open="open"
    :handleOnly="true"
    :prevent-close="isSubmitting || loading"
  >
    <template #title>
      <div class="flex justify-center px-4">
        <div class="space-y-5 w-2/3 max-w-[500px]">Покупка премиум</div>
      </div>
    </template>
    <template #description>
      <div class="flex justify-center px-4">
        <div class="space-y-5 w-2/3 max-w-[500px]">для {{ accountName }}</div>
      </div>
    </template>
    <template #body>
      <div class="flex justify-center px-4">
        <div class="space-y-5 w-2/3 max-w-[500px]">
          <div>
            <label class="block text-sm font-medium mb-1">
              Номер карты
              <span class="text-red-500">*</span>
            </label>
            <UInput
              v-model="formattedCardNumber"
              placeholder="1234 5678 9012 3456"
              icon="i-heroicons-credit-card"
              size="lg"
              maxlength="19"
              class="w-full"
              :error="!!errors.number"
              :ui="errors.number ? errorInputUi : {}"
              :disabled="isSubmitting"
            />
          </div>

          <div class="grid grid-cols-[1fr_1fr_auto] gap-4 items-end">
            <div class="grid grid-cols-[100px_10px_100px] items-end">
              <div>
                <label class="block text-sm font-medium mb-1">
                  Месяц
                  <span class="text-red-500">*</span>
                </label>
                <USelect
                  v-model="state.month"
                  :items="months"
                  placeholder="MM"
                  size="lg"
                  class="w-full"
                  :error="!!errors.month"
                  :ui="errors.month ? errorSelectUi : {}"
                  :disabled="isSubmitting"
                />
              </div>
              <div></div>
              <div>
                <label class="block text-sm font-medium mb-1">
                  Год
                  <span class="text-red-500">*</span>
                </label>
                <USelect
                  v-model="state.year"
                  :items="years"
                  placeholder="YY"
                  size="lg"
                  class="w-full"
                  :error="!!errors.year"
                  :ui="errors.year ? errorSelectUi : {}"
                  :disabled="isSubmitting"
                />
              </div>
            </div>

            <div class="w-20">
              <label class="block text-sm font-medium mb-1">
                CVV
                <span class="text-red-500">*</span>
              </label>
              <UInput
                v-model="state.cvv"
                type="password"
                placeholder="123"
                maxlength="3"
                icon="bx:lock"
                size="lg"
                :error="!!errors.cvv"
                :ui="errors.cvv ? errorInputUi : {}"
                :disabled="isSubmitting"
              />
            </div>
          </div>
        </div>
      </div>

      <div class="flex justify-center px-4">
        <div class="space-y-5 w-2/3 max-w-[500px] pt-4">
          <p v-for="(error, index) in activeErrors" :key="index" class="my-1 text-sm text-red-500">
            {{ error }}
          </p>

          <!-- Состояние загрузки -->
          <div
            v-if="loading && isSubmitting"
            class="flex flex-col items-center justify-center py-6 space-y-3"
          >
            <div
              class="w-8 h-8 border-4 border-blue-500 border-t-transparent rounded-full animate-spin"
            ></div>
            <p class="text-sm text-gray-600 dark:text-gray-400">
              Обработка запроса... Это может занять несколько секунд
            </p>
          </div>

          <!-- Результат запроса -->
          <div v-if="purchaseResponse && !loading" class="space-y-4 py-4">
            <!-- Ошибка -->
            <div v-if="purchaseResponse.status === 'error'" class="space-y-3">
              <div
                class="p-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg"
              >
                <p class="text-sm text-red-600 dark:text-red-400">
                  {{ purchaseResponse.message }}
                </p>
              </div>
              <UButton
                label="Закрыть"
                color="neutral"
                variant="outline"
                class="justify-center w-full"
                @click="closeDrawer"
              />
            </div>

            <!-- Успех с верификацией -->
            <div
              v-else-if="purchaseResponse.status === 'success' && purchaseResponse.verificationUrl"
              class="space-y-3"
            >
              <div
                class="p-4 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg"
              >
                <p class="text-sm text-blue-600 dark:text-blue-400">
                  Для завершения покупки необходимо пройти верификацию
                </p>
              </div>
              <UButton
                label="Перейти к верификации"
                color="primary"
                class="justify-center w-full"
                @click="openVerificationUrl"
              />
              <UButton
                label="Закрыть"
                color="neutral"
                variant="outline"
                class="justify-center w-full"
                @click="closeDrawer"
              />
            </div>

            <!-- Успех без верификации -->
            <div v-else-if="purchaseResponse.status === 'success'" class="space-y-3">
              <div
                class="p-4 bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-lg"
              >
                <p class="text-sm text-green-600 dark:text-green-400">
                  Premium успешно приобретен!
                </p>
              </div>
              <UButton
                label="Закрыть"
                color="neutral"
                variant="outline"
                class="justify-center w-full"
                @click="closeDrawer"
              />
            </div>
          </div>
        </div>
      </div>
    </template>

    <template #footer>
      <UButton
        v-if="!isSubmitting && !purchaseResponse"
        label="Купить"
        color="neutral"
        class="justify-center"
        @click="onSubmit"
        :disabled="loading"
      />
      <UButton
        v-if="!isSubmitting && !purchaseResponse"
        label="Закрыть"
        color="neutral"
        variant="outline"
        class="justify-center"
        @click="closeDrawer"
        :disabled="loading"
      />
    </template>
  </UDrawer>
</template>

<script setup lang="ts">
import { reactive, watch, ref, computed } from 'vue'
import { safeParse } from 'valibot'
import { useAccounts } from '@/composables/use-accounts'
import type { AccountOut, BuyPremiumOut } from '@/types/openapi'
import { cardDetailsSchema } from '@/schemas/card'

const props = defineProps<{ accountId: number }>()
const open = defineModel<boolean>('open', { default: false })

const emit = defineEmits<{
  (e: 'completed'): void
}>()

const { get, premium, loading } = useAccounts()

const account = ref<AccountOut | undefined>()
const purchaseResponse = ref<BuyPremiumOut | null>(null)
const isSubmitting = ref(false)

const state = reactive({
  number: '',
  month: undefined as number | undefined,
  year: undefined as number | undefined,
  cvv: '',
})

const errors = reactive({
  number: '',
  month: '',
  year: '',
  cvv: '',
  form: '',
})
const activeErrors = computed(() => {
  return Object.values(errors).filter((error) => error !== '')
})

const errorInputUi = {
  base: 'ring-1 ring-red-500 focus:ring-red-500 dark:ring-red-500 dark:focus:ring-red-500',
}

const errorSelectUi = {
  base: 'ring-1 ring-red-500 focus:ring-red-500 dark:ring-red-500 dark:focus:ring-red-500',
}

// Форматирование номера карты с пробелами
const formattedCardNumber = computed({
  get: () => {
    return (
      state.number
        .replace(/\s/g, '')
        .match(/.{1,4}/g)
        ?.join(' ') || state.number
    )
  },
  set: (value) => {
    state.number = value.replace(/\s/g, '')
  },
})

// Месяцы для селекта
const months = Array.from({ length: 12 }, (_, i) => ({
  value: i + 1,
  label: String(i + 1).padStart(2, '0'),
}))

// Годы для селекта (текущий + 10 лет)
const currentYear = new Date().getFullYear()
const years = Array.from({ length: 11 }, (_, i) => ({
  value: currentYear + i,
  label: String(currentYear + i),
}))

const accountName = computed(() => `${account?.value?.firstName} ${account?.value?.lastName}`)

// Загрузка данных
watch(
  [open, () => props.accountId],
  async ([isOpen, id]) => {
    if (isOpen && id) {
      account.value = await get(id)
      // Сброс ошибок и состояния при открытии
      Object.keys(errors).forEach((key) => {
        errors[key as keyof typeof errors] = ''
      })
      purchaseResponse.value = null
      isSubmitting.value = false
    }
  },
  { immediate: true },
)

const onSubmit = async () => {
  // Предотвращение повторных запросов
  if (isSubmitting.value || loading.value) {
    return
  }

  // Сброс ошибок
  Object.keys(errors).forEach((key) => {
    errors[key as keyof typeof errors] = ''
  })

  // Валидация
  const result = safeParse(cardDetailsSchema, state)

  if (!result.success) {
    // Обработка ошибок валидации
    result.issues.forEach((issue) => {
      // Проверяем, есть ли path (ошибка поля)
      if (issue.path && issue.path.length > 0) {
        const path = issue.path[0]?.key as keyof typeof errors
        if (path && path in errors) {
          errors[path] = issue.message
        }
      } else {
        // Это общая ошибка формы (например, "Карта просрочена")
        errors.form = issue.message
      }
    })
    return
  }

  isSubmitting.value = true
  const response = await premium(props.accountId, result.output)
  purchaseResponse.value = response
}

const openVerificationUrl = () => {
  if (purchaseResponse.value?.verificationUrl) {
    window.open(purchaseResponse.value.verificationUrl, '_blank')
  }
}

const closeDrawer = () => {
  open.value = false
  if (purchaseResponse.value?.status === 'success') {
    emit('completed')
  }
}
</script>
<style scoped>
.input-error :deep(input),
.input-error :deep(button) {
  border-color: rgb(239 68 68) !important;
}

.input-error :deep(input:focus),
.input-error :deep(button:focus) {
  border-color: rgb(239 68 68) !important;
}
</style>
