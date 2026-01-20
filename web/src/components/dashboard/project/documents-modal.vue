<template>
  <UModal v-model:open="open" title="Загрузка документов">
    <UButton label="Загрузить" icon="bx:upload" />
    <template #body>
      <UForm ref="form" :schema="projectDocumentsSchema" :state="state" @submit="onSubmit">
        <UFormField name="files">
          <UFileUpload
            v-model="state.files"
            multiple
            layout="list"
            label="Загрузите файлы TXT, MD"
            description="Не больше 20 МБ"
            class="w-full mb-4"
          />
        </UFormField>
        <div class="flex justify-end gap-2 w-full">
          <UButton label="Отмена" color="neutral" variant="outline" @click="open = false" />
          <UButton label="Отправить" type="submit" />
        </div>
      </UForm>
    </template>
  </UModal>
</template>
<script setup lang="ts">
import { nextTick, reactive, useTemplateRef, watch } from 'vue'
import type { FormSubmitEvent } from '@nuxt/ui'
import * as v from 'valibot'
import { useProjects } from '@/composables/use-projects'
import { useUploadStore } from '@/stores/upload-store'
import { useBackgroundJobs } from '@/stores/jobs-store'

const { projectId } = defineProps<{
  projectId: number
}>()
const jobsStore = useBackgroundJobs()

const { uploadAll, waitForAll } = useUploadStore()
const { saveDocuments } = useProjects()

const MAX_BYTES = 1024 * 1024 * 20 // 20 MB

// Схема для одного файла
const _projectDocumentSchema = v.pipe(
  v.file('Выберите файл'),
  v.mimeType(['text/plain'], 'Выберите TXT или MD'),
  v.maxSize(MAX_BYTES, 'Файл ≤ 20MB'),
)

// Схема для массива файлов
const projectDocumentsSchema = v.object({
  files: v.pipe(
    v.array(_projectDocumentSchema, 'Файлы должны быть массивом'),
    v.minLength(1, 'Выберите хотя бы один файл'), // опционально
    v.maxLength(10, 'Максимум 10 файлов'), // опционально
  ),
})

export type ProjectDocumentsSchema = v.InferOutput<typeof projectDocumentsSchema>

const emit = defineEmits<{
  (e: 'completed'): void
}>()

const open = defineModel<boolean>('open', { default: false })
const form = useTemplateRef('form')

const toast = useToast()

const state = reactive<ProjectDocumentsSchema>({
  files: [],
})

watch(
  open,
  async (open) => {
    if (open) {
      Object.assign(state, { files: [] })
      await nextTick()
      form.value?.clear()
    }
  },
  { immediate: true },
)

const onSubmit = async (event: FormSubmitEvent<ProjectDocumentsSchema>) => {
  open.value = false
  toast.add({
    title: 'Загрузка документов начата',
    color: 'success',
  })

  uploadAll(event.data.files, `media/project-${projectId}/documents`)
  const results = await waitForAll()
  if (results.fulfilled.length > 0) {
    const workflow = await saveDocuments(projectId, results.fulfilled)
    jobsStore.add({
      id: workflow.id,
      name: 'Загрузка документов',
      onComplete: () => {
        toast.add({
          title: 'Загрузка документов завершена',
          color: 'success',
        })
        emit('completed')
      },
    })
  } else {
    toast.add({
      title: 'Загрузка не удалась',
      description: 'обратитесь в техподдержку',
      color: 'error',
    })
  }
  form.value?.clear()
}
</script>
<style scoped>
:deep(.tab-panel) {
  min-height: 200px;
  height: 200px;
  display: flex;
  flex-direction: column;
}
</style>
