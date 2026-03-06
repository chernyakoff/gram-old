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
                <UInput
                  :model-value="monthDisplay"
                  placeholder="MM"
                  maxlength="2"
                  size="lg"
                  type="text"
                  inputmode="numeric"
                  :error="!!errors.month"
                  :ui="errors.month ? errorInputUi : {}"
                  :disabled="isSubmitting"
                  @input="handleMonthInput"
                  @blur="formatMonth"
                  @keypress="onlyNumbers"
                />
              </div>

              <div class="flex items-center justify-center pb-2">
                <span class="text-gray-400">/</span>
              </div>

              <!-- Год -->
              <div>
                <label class="block text-sm font-medium mb-1">
                  Год
                  <span class="text-red-500">*</span>
                </label>
                <UInput
                  :model-value="yearDisplay"
                  placeholder="YY"
                  maxlength="2"
                  size="lg"
                  type="text"
                  inputmode="numeric"
                  :error="!!errors.year"
                  :ui="errors.year ? errorInputUi : {}"
                  :disabled="isSubmitting"
                  @input="handleYearInput"
                  @blur="formatYear"
                  @keypress="onlyNumbers"
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

const monthDisplay = ref('')
const yearDisplay = ref('')

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

const accountName = computed(
  () => `${account.value?.firstName ?? ''} ${account.value?.lastName ?? ''}`,
)

// Блокировка ввода нечисловых символов
const onlyNumbers = (event: KeyboardEvent) => {
  const char = event.key
  // Разрешаем только цифры и служебные клавиши
  if (
    !/^\d$/.test(char) &&
    !['Backspace', 'Delete', 'ArrowLeft', 'ArrowRight', 'Tab'].includes(char)
  ) {
    event.preventDefault()
  }
}

// Обработка ввода месяца
const handleMonthInput = (event: Event) => {
  const target = event.target as HTMLInputElement
  let value = target.value.replace(/\D/g, '') // Только цифры

  if (value.length === 0) {
    monthDisplay.value = ''
    state.month = undefined
    return
  }

  // Ограничиваем до 2 цифр
  if (value.length > 2) {
    value = value.slice(0, 2)
  }

  // Если вводим вторую цифру
  if (value.length === 2) {
    let numValue = parseInt(value)

    // Если больше 12, заменяем на 12
    if (numValue > 12) {
      value = '12'
      numValue = 12
    } else if (numValue < 1) {
      value = '01'
      numValue = 1
    }

    monthDisplay.value = value
    state.month = numValue
    return
  }

  // Если одна цифра
  if (value.length === 1) {
    const firstDigit = parseInt(value)

    // Если первая цифра больше 1, автоматически делаем полный месяц
    if (firstDigit > 1) {
      value = '0' + value
      monthDisplay.value = value
      state.month = firstDigit
      return
    }

    // Иначе просто показываем одну цифру
    monthDisplay.value = value
    state.month = undefined
  }
}

// Форматирование месяца при потере фокуса
const formatMonth = () => {
  if (monthDisplay.value && monthDisplay.value.length === 1) {
    monthDisplay.value = '0' + monthDisplay.value
  }

  // Валидация при потере фокуса
  if (state.month) {
    validateExpiry()
  }
}

// Обработка ввода года
const handleYearInput = (event: Event) => {
  const target = event.target as HTMLInputElement
  let value = target.value.replace(/\D/g, '') // Только цифры

  if (value.length === 0) {
    yearDisplay.value = ''
    state.year = undefined
    return
  }

  // Ограничиваем до 2 цифр
  if (value.length > 2) {
    value = value.slice(0, 2)
  }

  yearDisplay.value = value

  // Преобразуем в полный год только если 2 цифры
  if (value.length === 2) {
    const currentYear = new Date().getFullYear()
    const currentCentury = Math.floor(currentYear / 100) * 100
    const fullYear = currentCentury + parseInt(value)
    state.year = fullYear
  } else {
    state.year = undefined
  }
}

// Форматирование года при потере фокуса
const formatYear = () => {
  if (yearDisplay.value && yearDisplay.value.length === 1) {
    yearDisplay.value = '0' + yearDisplay.value
    const currentYear = new Date().getFullYear()
    const currentCentury = Math.floor(currentYear / 100) * 100
    const fullYear = currentCentury + parseInt(yearDisplay.value)
    state.year = fullYear
  }

  // Валидация при потере фокуса
  if (state.year) {
    validateExpiry()
  }
}

// Валидация срока действия карты
const validateExpiry = () => {
  // Сбрасываем ошибки месяца и года
  errors.month = ''
  errors.year = ''
  errors.form = ''

  const month = state.month
  const year = state.year

  // Если заполнены оба поля
  if (month && year) {
    const now = new Date()
    const currentYear = now.getFullYear()
    const currentMonth = now.getMonth() + 1

    // Проверка на просроченную карту
    if (year < currentYear || (year === currentYear && month < currentMonth)) {
      errors.form = 'Карта просрочена'
    }
  }
}

// Загрузка данных при открытии
watch(
  [open, () => props.accountId],
  async ([isOpen, id]) => {
    if (!isOpen || !id) return

    account.value = await get(id)
    resetErrors()
    purchaseResponse.value = null
    isSubmitting.value = false

    // Сброс полей при открытии
    monthDisplay.value = ''
    yearDisplay.value = ''
    state.month = undefined
    state.year = undefined
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
