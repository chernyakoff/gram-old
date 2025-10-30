<template>
  <UDrawer direction="right" class="w-160" :handle="false" v-model:open="open" :handleOnly="true">
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
        <UForm
          ref="form"
          :schema="cardDetailsSchema"
          :state="state"
          class="space-y-5 w-2/3 max-w-[500px]"
          @submit="onSubmit"
        >
          <UFormField label="Номер карты" name="number" required>
            <UInput
              v-model="formattedCardNumber"
              placeholder="1234 5678 9012 3456"
              icon="i-heroicons-credit-card"
              size="lg"
              maxlength="19"
              class="w-full"
            />
          </UFormField>

          <div class="grid grid-cols-[1fr_1fr_auto] gap-4 items-end">
            <div class="grid grid-cols-[75px_10px_75px] items-end">
              <UFormField label="Месяц" name="month" required>
                <USelect v-model="state.month" :items="months" placeholder="MM" size="lg" />
              </UFormField>
              <div></div>
              <UFormField label="Год" name="year" required>
                <USelect v-model="state.year" :items="years" placeholder="YY" size="lg" />
              </UFormField>
            </div>

            <UFormField label="CVV" name="cvv" required class="w-20">
              <UInput
                v-model="state.cvv"
                type="password"
                placeholder="123"
                maxlength="3"
                icon="bx:lock"
                size="lg"
              />
            </UFormField>
          </div>
        </UForm>
      </div>
    </template>

    <template #footer>
      <UButton label="Купить" color="neutral" class="justify-center" @click="doSubmit" />
      <UButton
        label="Закрыть"
        color="neutral"
        variant="outline"
        class="justify-center"
        @click="open = false"
      />
    </template>
  </UDrawer>
</template>

<script setup lang="ts">
import { reactive, watch, ref, computed, useTemplateRef } from 'vue'
import { useAccounts } from '@/composables/use-accounts'
import { useBackgroundJobs } from '@/stores/jobs-store'
import type { AccountOut } from '@/types/openapi'
import { cardDetailsSchema, type CardDetailsSchema } from '@/schemas/card'
import type { FormSubmitEvent } from '@nuxt/ui'

const props = defineProps<{ accountId: number }>()
const open = defineModel<boolean>('open', { default: false })

const emit = defineEmits<{
  (e: 'completed'): void
}>()

const toast = useToast()
const form = useTemplateRef('form')

const { get, update } = useAccounts()

const jobsStore = useBackgroundJobs()

const account = ref<AccountOut | undefined>()

const state = reactive({
  number: '',
  month: undefined as number | undefined,
  year: undefined as number | undefined,
  cvv: '',
})
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
    }
  },
  { immediate: true },
)

const doSubmit = async () => {
  await form.value?.submit()
}

const onSubmit = async (event: FormSubmitEvent<CardDetailsSchema>) => {
  toast.add({
    title: 'Обновление данных аккаунта запущено',
    description: 'Можно посмотреть ход выполнения в разделе «задачи»',
    color: 'success',
  })

  /* const { id } = await update(props.accountId, payload)

  jobsStore.add({
    id,
    name: 'Обновление аккаунта',
    onComplete: () => emit('completed'),
  }) */
}
</script>
