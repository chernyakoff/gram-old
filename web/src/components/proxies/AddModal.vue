<template>
  <UModal v-model:open="open" title="Загрузка прокси" description="socks5">
    <UButton label="Добавить" icon="i-lucide-plus" />
    <template #body>
      <UTabs :items="items" variant="link" :ui="{ trigger: 'grow' }" class="gap-4 w-full">
        <template #text>
          <div class="tab-panel">
            <UTextarea v-model="textValue" placeholder="ip:port:login:pass" class="w-full h-full resize-none" />
          </div>
        </template>
        <template #file>
          <div class="tab-panel">
            <UFileUpload v-model="fileValue" class="w-full h-full" />
          </div>
        </template>
      </UTabs>
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
import type { TabsItem } from '@nuxt/ui'
import { useProxies } from '@/composables/useProxies'
import { useBackgroundJobs } from '@/stores/jobs'


const emit = defineEmits<{
  (e: 'close'): void,
  (e: 'completed'): void,
}>();

const open = ref(false)

const toast = useToast()

const isSubmitDisabled = computed(() => {
  return !textValue.value.trim() && !fileValue.value
})

const textValue = ref('')
const fileValue = ref<File | null>(null)

const { upload } = useProxies()

const jobsStore = useBackgroundJobs()


const items = [
  {
    label: 'Списком',
    description: 'Make changes to your account here. Click save when you\'re done.',
    icon: 'i-lucide-list', // или 'running'
    slot: 'text' as const
  },
  {
    label: 'Файлом',
    description: 'Change your password here. After saving, you\'ll be logged out.',
    icon: 'i-lucide-file',
    slot: 'file' as const
  }
] satisfies TabsItem[]


// TODO: не заюыть обнулить при открытии


async function handleUpload () {
  open.value = false
  emit('close')

  toast.add({ title: 'Загрузка прокси начата', description: `Можно посмотреть ход выполнения в разделе «задачи»`, color: 'success' })
  const { id } = await upload({ text: textValue.value, file: fileValue.value || undefined })
  jobsStore.add({
    id,
    name: "Загрузка прокси",
    onComplete: () => emit('completed')
  })

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
