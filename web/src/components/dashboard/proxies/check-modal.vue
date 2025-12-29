<template>
  <UModal
    v-model:open="open"
    title="Проверка"
    :description="`Будет проверено ${selectedIds.length} прокси.`"
  >
    <UButton
      v-if="selectedIds.length"
      label="Проверить"
      color="neutral"
      variant="subtle"
      icon="bx:world"
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
        <UButton label="Изменить" color="primary" variant="solid" loading-auto @click="onSubmit" />
      </div>
    </template>
  </UModal>
</template>
<script setup lang="ts">
import type { ProxiesCheckIn } from '@/types/openapi'
import { useProxies } from '@/composables/use-proxies'
import { useBackgroundJobs } from '@/stores/jobs-store'

const jobsStore = useBackgroundJobs()

const toast = useToast()

const emit = defineEmits<{
  (e: 'completed'): void
}>()

const { selectedIds } = defineProps<{
  selectedIds: number[]
}>()

const open = defineModel<boolean>('open', { default: false })

const { check } = useProxies()

async function onSubmit() {
  open.value = false
  toast.add({
    title: 'Проверка прокси запущена',
    description: `Можно посмотреть ход выполнения в разделе «задачи»`,
    color: 'success',
  })

  const data: ProxiesCheckIn = {
    ids: selectedIds,
  }

  try {
    const { id } = await check(data)
    jobsStore.add({
      id,
      name: 'Проверка прокси',
      onComplete: () => emit('completed'),
    })
  } catch (e: unknown) {
    console.error(e)
  }
  await check(data)
}
</script>
