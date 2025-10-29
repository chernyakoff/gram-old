<template>
  <UModal v-model:open="open" title=" аккаунтов" description="session/json">
    <template #body>
      <div class="tab-panel">
        <UFileUpload v-model="fileValue" class="w-full h-full" label="ZIP" />
      </div>
    </template>
    <template #footer="{ close }">
      <div class="flex justify-end gap-2 w-full">
        <UButton label="Отмена" color="neutral" variant="outline" @click="close" />
        <UButton :disabled="isSubmitDisabled" label="Отправить" @click="handleUpload" />
      </div>
    </template>
  </UModal>
</template>
<script setup lang="ts">
import { computed, ref } from 'vue'
import { useAccounts } from '@/composables/use-accounts'
import { useBackgroundJobs } from '@/stores/jobs-store'

const { upload } = useAccounts()
const jobsStore = useBackgroundJobs()

const emit = defineEmits<{
  (e: 'completed'): void
}>()

const toast = useToast()
const open = ref(false)
const fileValue = ref<File | null>(null)
const isSubmitDisabled = computed(() => {
  return !fileValue.value
})

async function handleUpload() {
  open.value = false
  toast.add({
    title: 'Загузка аккаунтов запущена',
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
}
</script>
