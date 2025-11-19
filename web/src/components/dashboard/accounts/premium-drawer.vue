<template>
  <UDrawer
    direction="right"
    class="w-160"
    :handle="false"
    v-model:open="open"
    :prevent-close="isSubmitting || localLoading"
  >
    <!-- Заголовок -->
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

    <!-- Тело -->
    <template #body>
      <div class="flex justify-center px-4">
        <div class="space-y-5 w-2/3 max-w-[500px]">
          <!-- Номер карты -->
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

          <!-- Дата + CVV -->
          <div class="grid grid-cols-[1fr_1fr_auto] gap-4 items-end">
            <div class="grid grid-cols-[100px_10px_100px] items-end">
              <!-- Месяц -->
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
                  :error="!!errors.month"
                  :ui="errors.month ? errorSelectUi : {}"
                  :disabled="isSubmitting"
                />
              </div>

              <div></div>

              <!-- Год -->
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
                  :error="!!errors.year"
                  :ui="errors.year ? errorSelectUi : {}"
                  :disabled="isSubmitting"
                />
              </div>
            </div>

            <!-- CVV -->
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

      <!-- Ошибки формы -->
      <div class="flex justify-center px-4">
        <div class="space-y-5 w-2/3 max-w-[500px] pt-4">
          <p v-for="(error, index) in activeErrors" :key="index" class="my-1 text-sm text-red-500">
            {{ error }}
          </p>

          <!-- Загрузка -->
          <div v-if="localLoading" class="flex flex-col items-center justify-center py-6 space-y-3">
            <div
              class="w-8 h-8 border-4 border-blue-500 border-t-transparent rounded-full animate-spin"
            ></div>
            <p class="text-sm text-gray-600 dark:text-gray-400">Обработка запроса...</p>
          </div>

          <!-- Результат -->
          <div v-if="purchaseResponse && !localLoading" class="space-y-4 py-4">
            <!-- Ошибка -->
            <template v-if="purchaseResponse.status === 'error'">
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
            </template>

            <!-- Успех с верификацией -->
            <template
              v-else-if="purchaseResponse.status === 'success' && purchaseResponse.verificationUrl"
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
            </template>

            <!-- Успех -->
            <template v-else>
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
            </template>
          </div>
        </div>
      </div>
    </template>

    <!-- Футер -->
    <template #footer>
      <div v-if="!purchaseResponse" class="flex gap-4 justify-end">
        <UButton label="Купить" color="neutral" @click="onSubmit" :disabled="localLoading" />
        <UButton
          label="Закрыть"
          color="neutral"
          variant="outline"
          @click="closeDrawer"
          :disabled="localLoading"
        />
      </div>
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

const { get, premium } = useAccounts()

const account = ref<AccountOut | undefined>()
const purchaseResponse = ref<BuyPremiumOut | null>(null)
const isSubmitting = ref(false)
const localLoading = ref(false)

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

const resetErrors = () => {
  ;(Object.keys(errors) as Array<keyof typeof errors>).forEach((key) => {
    errors[key] = ''
  })
}

const activeErrors = computed(() => Object.values(errors).filter(Boolean))

const errorInputUi = {
  base: 'ring-1 ring-red-500 focus:ring-red-500 dark:ring-red-500 dark:focus:ring-red-500',
}
const errorSelectUi = errorInputUi

// Форматирование номера
const formattedCardNumber = computed({
  get: () =>
    state.number
      .replace(/\s/g, '')
      .match(/.{1,4}/g)
      ?.join(' ') || state.number,
  set: (value) => {
    state.number = value.replace(/\s/g, '')
  },
})

// Месяцы
const months = Array.from({ length: 12 }, (_, i) => ({
  value: i + 1,
  label: String(i + 1).padStart(2, '0'),
}))

// Годы
const currentYear = new Date().getFullYear()
const years = Array.from({ length: 11 }, (_, i) => ({
  value: currentYear + i,
  label: String(currentYear + i),
}))

const accountName = computed(
  () => `${account.value?.firstName ?? ''} ${account.value?.lastName ?? ''}`,
)

// Загрузка данных при открытии
watch(
  [open, () => props.accountId],
  async ([isOpen, id]) => {
    if (!isOpen || !id) return

    account.value = await get(id)
    resetErrors()
    purchaseResponse.value = null
    isSubmitting.value = false
  },
  { immediate: true },
)

const onSubmit = async () => {
  if (isSubmitting.value || localLoading.value) return

  isSubmitting.value = true
  localLoading.value = true
  resetErrors()

  const result = safeParse(cardDetailsSchema, state)

  if (!result.success) {
    for (const issue of result.issues) {
      const key = issue.path?.[0]?.key as keyof typeof errors
      if (key && key in errors) errors[key] = issue.message
      else errors.form = issue.message
    }
    localLoading.value = false
    isSubmitting.value = false
    return
  }

  try {
    purchaseResponse.value = await premium(props.accountId, result.output)
  } finally {
    localLoading.value = false
    isSubmitting.value = false
  }
}

const openVerificationUrl = () => {
  const url = purchaseResponse.value?.verificationUrl
  if (url) window.open(url, '_blank')
}

const closeDrawer = () => {
  open.value = false
  if (purchaseResponse.value?.status === 'success') emit('completed')
}
</script>
