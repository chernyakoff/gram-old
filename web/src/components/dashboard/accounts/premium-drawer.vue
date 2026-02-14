<template>
  <UDrawer
    direction="right"
    class="w-160"
    :handle="false"
    v-model:open="open"
    :prevent-close="isSubmitting || localLoading">
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
            <label class="block text-sm font-medium mb-1"> Номер карты <span class="text-red-500">*</span>
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
              :disabled="isSubmitting" />
          </div>
          <!-- Дата + CVV -->
          <div class="grid grid-cols-[1fr_1fr_auto] gap-4 items-end">
            <div class="grid grid-cols-[100px_10px_100px] items-end">
              <!-- Месяц -->
              <div>
                <label class="block text-sm font-medium mb-1"> Месяц <span class="text-red-500">*</span>
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
                  @keypress="onlyNumbers" />
              </div>
              <div class="flex items-center justify-center pb-2">
                <span class="text-gray-400">/</span>
              </div>
              <!-- Год -->
              <div>
                <label class="block text-sm font-medium mb-1"> Год <span class="text-red-500">*</span>
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
                  @keypress="onlyNumbers" />
              </div>
            </div>
            <!-- CVV -->
            <div class="w-20">
              <label class="block text-sm font-medium mb-1"> CVV <span class="text-red-500">*</span>
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
                :disabled="isSubmitting" />
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
              class="w-8 h-8 border-4 border-blue-500 border-t-transparent rounded-full animate-spin"></div>
            <p class="text-sm text-gray-600 dark:text-gray-400">Обработка запроса...</p>
          </div>
          <!-- Результат -->
          <div v-if="purchaseResponse && !localLoading" class="space-y-4 py-4">
            <!-- Ошибка -->
            <template v-if="purchaseResponse.status === 'error'">
              <div
                class="p-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg">
                <p class="text-sm text-red-600 dark:text-red-400">
                  {{ purchaseResponse.message }}
                </p>
              </div>
              <UButton
                label="Закрыть"
                color="neutral"
                variant="outline"
                class="justify-center w-full"
                @click="closeDrawer" />
            </template>
            <!-- Успех -->
            <template v-else-if="purchaseResponse.status === 'success'">
              <div
                class="p-4 bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-lg">
                <div class="space-y-2">
                  <p class="text-sm text-green-600 dark:text-green-400"> Запрос на покупку premium отправлен. </p>
                  <p v-if="purchaseResponse.message" class="text-sm text-green-600 dark:text-green-400">
                    {{ purchaseResponse.message }}
                  </p>
                  <p class="text-sm text-green-600 dark:text-green-400"> Дальше нужно вручную проверить, появился ли premium у аккаунта, и подтвердить результат. </p>
                </div>
              </div>
              <div class="p-4 bg-white dark:bg-gray-900/20 border border-gray-200 dark:border-gray-800 rounded-lg">
                <div class="space-y-2">
                  <p class="text-sm text-gray-700 dark:text-gray-300"> Инструкция: </p>
                  <ol class="list-decimal list-inside text-sm text-gray-700 dark:text-gray-300 space-y-1">
                    <li v-if="purchaseResponse.verificationUrl"> Нажмите «Перейти к верификации» и завершите 3DS/подтверждение оплаты в банке. </li>
                    <li> Нажмите «Проверка премиум» и откройте профиль аккаунта в Telegram. </li>
                    <li> Убедитесь, что у аккаунта есть синяя звездочка premium. </li>
                    <li> Вернитесь сюда и нажмите «Премиум куплен» или «Премиум не куплен». </li>
                  </ol>
                </div>
              </div>
              <div class="grid grid-cols-1 gap-2">
                <UButton
                  v-if="purchaseResponse.verificationUrl"
                  label="Перейти к верификации"
                  color="primary"
                  class="justify-center w-full"
                  @click="openVerificationUrl" />
                <UButton
                  label="Проверка премиум"
                  color="neutral"
                  variant="outline"
                  class="justify-center w-full"
                  @click="openUsernameUrl" />
                <UButton
                  label="Премиум куплен"
                  color="primary"
                  class="justify-center w-full"
                  :disabled="localLoading"
                  @click="confirmPurchased(true)" />
                <UButton
                  label="Премиум не куплен"
                  color="neutral"
                  variant="outline"
                  class="justify-center w-full"
                  :disabled="localLoading"
                  @click="confirmPurchased(false)" />
              </div>
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
          :disabled="localLoading" />
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
import { useBackgroundJobs } from '@/stores/jobs-store'

const props = defineProps<{ accountId: number }>()
const open = defineModel<boolean>('open', { default: false })

const emit = defineEmits<{
  (e: 'completed'): void
}>()

const jobsStore = useBackgroundJobs()
const toast = useToast()

const { get, premium, confirmPremium } = useAccounts()

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
  ; (Object.keys(errors) as Array<keyof typeof errors>).forEach((key) => {
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

  if (!account.value?.username) {
    errors.form = 'Для покупки premium установите аккаунту username'
    localLoading.value = false
    isSubmitting.value = false
    return
  }

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

function usernameUrl () {
  const u = account.value?.username
  if (!u) return null
  const clean = u.startsWith('@') ? u.slice(1) : u
  return `https://t.me/${clean}`
}

const openUsernameUrl = () => {
  const url = usernameUrl()
  if (url) window.open(url, '_blank')
}

const confirmPurchased = async (purchased: boolean) => {
  if (!account.value?.username) {
    toast.add({
      title: 'Нужен username',
      description: 'Для проверки и подтверждения нужен username у аккаунта.',
      color: 'warning',
    })
    return
  }

  localLoading.value = true
  try {
    const res = await confirmPremium(props.accountId, purchased)
    if (purchased && res.stopWorkflowId) {
      jobsStore.add({
        id: res.stopWorkflowId,
        name: `Отмена подписки ${account.value?.phone ?? ''}`,
        onComplete: () => emit('completed'),
      })
    } else {
      emit('completed')
    }

    toast.add({
      title: purchased ? 'Premium подтвержден' : 'Premium не подтвержден',
      description: purchased
        ? 'Сохранили статус premium и запустили отмену автосписания.'
        : 'Сохранили, что premium не куплен.',
      color: 'success',
    })

    open.value = false
  } catch {
    toast.add({
      title: 'Ошибка',
      description: 'Не удалось сохранить подтверждение. Попробуйте еще раз.',
      color: 'error',
    })
  } finally {
    localLoading.value = false
  }
}

const closeDrawer = () => {
  open.value = false
}
</script>
