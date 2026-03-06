<template>
  <UModal
    v-model:open="open"
    title="Генератор"
    :description="`Будет запущено для ${props.selectedIds.length} ${plur(props.selectedIds.length)}.`">
    <UButton
      v-if="props.selectedIds.length && !props.hideTrigger"
      label="Генератор"
      color="neutral"
      variant="subtle"
      icon="bx:wand">
      <template #trailing>
        <UKbd>
          {{ props.selectedIds.length }}
        </UKbd>
      </template>
    </UButton>
    <template #body>
      <div class="grid grid-cols-2 gap-4">
        <UFormField label="Генерировать" name="generate">
          <div class="flex flex-col gap-2">
            <UCheckbox v-model="generateNames" label="Имена" />
            <UCheckbox v-model="generateUsernames" label="Юзернеймы" />
          </div>
        </UFormField>
        <UFormField label="Пол" name="gender">
          <USelectMenu
            v-model="gender"
            :items="genderItems"
            value-key="value"
            class="w-full" />
        </UFormField>
      </div>
    </template>
    <template #footer>
      <div class="flex justify-end gap-2">
        <UButton label="Отмена" color="neutral" variant="subtle" @click="open = false" />
        <UButton
          label="Запуск"
          color="primary"
          variant="solid"
          :disabled="!canSubmit"
          loading-auto
          @click="onSubmit" />
      </div>
    </template>
  </UModal>
</template>
<script setup lang="ts">
import { computed, ref } from 'vue'
import type { SelectMenuItem } from '@nuxt/ui'

import { pluralize } from '@/utils/pluralize'
import { useAccounts } from '@/composables/use-accounts'

import { useBackgroundJobs } from '@/stores/jobs-store'
import type { AccountsGenerateIn } from '@/types/openapi'

const toast = useToast()
const { generate } = useAccounts()
const jobsStore = useBackgroundJobs()

const emit = defineEmits<{
  (e: 'completed'): void
}>()

const props = withDefaults(defineProps<{
  selectedIds: number[]
  hideTrigger?: boolean
}>(), {
  hideTrigger: false,
})

const open = defineModel<boolean>('open', { default: false })

const gender = ref<AccountsGenerateIn['gender']>('any')
const generateNames = ref(true)
const generateUsernames = ref(true)
const canSubmit = computed(() => generateNames.value || generateUsernames.value)

const genderItems: SelectMenuItem[] = [
  { label: 'Любой', value: 'any' },
  { label: 'Мужские', value: 'male' },
  { label: 'Женские', value: 'female' },
]

const plur = (n: number): string => {
  return pluralize(n, ['аккаунт', 'аккаунта', 'аккаунтов'])
}

async function onSubmit () {
  open.value = false

  toast.add({
    title: 'Генерация запущена',
    description: 'Можно посмотреть ход выполнения в разделе «задачи»',
    color: 'success',
  })

  try {
    const payload: AccountsGenerateIn = {
      ids: props.selectedIds,
      gender: gender.value,
      generateNames: generateNames.value,
      generateUsernames: generateUsernames.value,
    }
    const { id } = await generate(payload)
    jobsStore.add({
      id,
      name: 'Генератор',
      onComplete: () => emit('completed'),
    })
  } catch (e: unknown) {
    console.error(e)
  }
}
</script>
