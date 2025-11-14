<template>
  <UModal
    v-model:open="open"
    :title="`Установить лимит`"
    :description="`Будет установлено для ${selectedIds.length} ${plur(selectedIds.length)}.`"
  >
    <UButton
      v-if="selectedIds.length"
      label="Установить лимит"
      color="neutral"
      variant="subtle"
      icon="bx:link"
    >
      <template #trailing>
        <UKbd>
          {{ selectedIds.length }}
        </UKbd>
      </template>
    </UButton>
    <template #body>
      <UFormField label="Новых диалогов в день" name="outDailyLimit" class="mb-4">
        <UInputNumber v-model="outDailyLimit" size="md" />
      </UFormField>
    </template>
    <template #footer>
      <div class="flex justify-end gap-2">
        <UButton label="Отмена" color="neutral" variant="subtle" @click="open = false" />
        <UButton label="Назначить" color="primary" variant="solid" loading-auto @click="onSubmit" />
      </div>
    </template>
  </UModal>
</template>
<script setup lang="ts">
import { ref } from 'vue'

import { pluralize } from '@/utils/pluralize'
import { useAccounts } from '@/composables/use-accounts'
import type { SetLimitIn } from '@/types/openapi'

const emit = defineEmits<{
  (e: 'close'): void
}>()

const outDailyLimit = ref(6)

const { selectedIds } = defineProps<{
  selectedIds: number[]
}>()

const open = defineModel<boolean>('open', { default: false })
const error = ref<string | undefined>(undefined)

const plur = (n: number): string => {
  return pluralize(n, ['аккаунт', 'аккаунта', 'аккаунтов'])
}

const { setLimit } = useAccounts()

async function onSubmit() {
  if (!outDailyLimit.value) {
    error.value = 'Пожалуйста, назначьте лимит'
    return
  }

  error.value = undefined

  const data: SetLimitIn = {
    outDailyLimit: outDailyLimit.value,
    accountIds: selectedIds,
  }

  await setLimit(data)
  open.value = false
  emit('close')
}
</script>
