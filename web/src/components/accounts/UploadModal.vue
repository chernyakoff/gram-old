<template>
  <UModal v-model:open="open" title="Загрузка аккаунтов" description="session/json">
    <UButton label="Добавить" icon="i-lucide-plus" />
    <template #body>
      <div class="tab-panel">
        <UFileUpload v-model="fileValue" class="w-full h-full" />
      </div>
    </template>
    <template #footer="{ close }">
      <div class="flex justify-end gap-2 w-full">
        <UButton
          label="Отмена"
          color="neutral"
          variant="outline"
          @click="close" />
        <UButton
          :disabled="isSubmitDisabled"
          label="Отправить"
          @click="handleUpload" />
      </div>
    </template>
  </UModal>
</template>
<script setup lang="ts">
import { computed, ref } from 'vue'
import { useAccounts } from '@/composables/useAccounts'
import { useBackgroundJobs } from '@/stores/jobs'

const { upload } = useAccounts()
const jobsStore = useBackgroundJobs()

const emit = defineEmits<{
  (e: 'completed'): void,
}>();

const toast = useToast()
const open = ref(false)
const fileValue = ref<File | null>(null)
const isSubmitDisabled = computed(() => {
  return !fileValue.value
})



async function handleUpload () {
  open.value = false
  toast.add({
    title: 'Обновления данных аккаунта запущено',
    description: `Можно посмотреть ход выполнения в разделе «задачи»`,
    color: 'success'
  })
  try {
    const { id } = await upload(fileValue.value!)
    jobsStore.add({
      id,
      name: "Загрузка аккаунтов",
      onComplete: () => emit('completed')
    })

  } catch (e: unknown) {
    console.error(e)
  }
}
</script>
<style scoped>
:deep(.tab-panel) {
  min-height: 200px;
  height: 200px;
  display: flex;
  flex-direction: column;
}

:deep(.tab-panel textarea) {
  height: 100% !important;
  min-height: 0 !important;
  resize: none !important;
}
</style>
