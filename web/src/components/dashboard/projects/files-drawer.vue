<template>
  <UDrawer
    direction="right"
    title="Файлы проекта"
    description="создайте базу знаний для ваших AI агентов"
    v-model:open="open"
  >
    <UButton variant="ghost" icon="lucide:files" title="Файлы" />
    <template #body>
      <UFileUpload
        v-model="files"
        multiple
        accept="text/*"
        layout="list"
        label="Загрузите текстовые файлы"
        description="TXT, MD, CSV и другие текстовые форматы"
        class="w-96 min-h-48"
      />
      <UButton
        label="Сохранить"
        :disabled="files.length < 1"
        color="neutral"
        class="justify-center"
        @click="onSubmit"
      />
    </template>
  </UDrawer>
</template>
<script setup lang="ts">
import { ref, watch } from 'vue'
const open = defineModel<boolean>('open', { default: false })
const { uploadAll, waitForAll } = useUploadStore()
const jobsStore = useBackgroundJobs()
const files = ref<File[]>([])

watch(open, (isOpen) => {
  if (!isOpen) {
    files.value = []
  }
})
// не забудь валидацию
async function onSubmit() {}
</script>
