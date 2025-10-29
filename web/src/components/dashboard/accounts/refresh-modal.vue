<template>
  <div></div>
  <!--  <UModal
    v-model:open="open"
    :title="`Обновление данных`"
    :description="`Будет обновлено ${selectedIds.length} ${plur(selectedIds.length)}.`"
  >
    <UButton
      v-if="selectedIds.length"
      label="Обновить данные"
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

    <template #footer>
      <div class="flex justify-end gap-2">
        <UButton label="Отмена" color="neutral" variant="subtle" @click="open = false" />
        <UButton label="Обновить" color="primary" variant="solid" loading-auto @click="onSubmit" />
      </div>
    </template>
  </UModal> -->
</template>
<script setup lang="ts">
/*
import { useBackgroundJobs } from '@/stores/jobs-store'

import { pluralize } from '@/utils/pluralize'
import { useAccounts } from '@/composables/use-accounts'

const toast = useToast()

const jobsStore = useBackgroundJobs()

const emit = defineEmits<{
  (e: 'completed'): void
}>()

const { selectedIds } = defineProps<{
  selectedIds: number[]
}>()

const open = defineModel<boolean>('open', { default: false })

const plur = (n: number): string => {
  return pluralize(n, ['аккаунт', 'аккаунта', 'аккаунтов'])
}

async function onSubmit() {
  open.value = false
  toast.add({
    title: 'Обновление данных аккаунтов запущено',
    description: `Можно посмотреть ход выполнения в разделе «задачи»`,
    color: 'success',
  })

  try {
    const { id } = await upload(fileValue.value!)
    jobsStore.add({
      id,
      name: 'Загрузка аккаунтов',
      onComplete: () => emit('completed'),
    })
  } catch (e: unknown) {
    console.error(e)
  }
} */
</script>
