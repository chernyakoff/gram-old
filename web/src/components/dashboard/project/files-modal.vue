<template>
  <UModal v-model:open="open" title="Загрузка файлов">
    <UButton label="Загрузить" icon="bx:upload" />
    <template #body>
      <UForm ref="form" :schema="projectFilesSchema" :state="state" @submit="onSubmit">
        <UFormField name="files">
          <UFileUpload
            v-model="state.files"
            multiple
            layout="list"
            label="Загрузите файлы"
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

const { projectId } = defineProps<{
  projectId: number
}>()

const { uploadAll, waitForAll } = useUploadStore()
const { saveFiles } = useProjects()

const MAX_BYTES = 1024 * 1024 * 20 // 20 MB

// Схема для одного файла
const _projectFileSchema = v.pipe(
  v.file('Выберите файл'),

  v.maxSize(MAX_BYTES, 'Файл ≤ 20MB'),
)

// Схема для массива файлов
const projectFilesSchema = v.object({
  files: v.pipe(
    v.array(_projectFileSchema, 'Файлы должны быть массивом'),
    v.minLength(1, 'Выберите хотя бы один файл'), // опционально
    v.maxLength(10, 'Максимум 10 файлов'), // опционально
  ),
})

export type ProjectFilesSchema = v.InferOutput<typeof projectFilesSchema>

const emit = defineEmits<{
  (e: 'completed'): void
}>()

const open = defineModel<boolean>('open', { default: false })
const form = useTemplateRef('form')

const toast = useToast()

const state = reactive<ProjectFilesSchema>({
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

const onSubmit = async (event: FormSubmitEvent<ProjectFilesSchema>) => {
  console.log(101)
  open.value = false
  toast.add({
    title: 'Загрузка файлов начата',
    color: 'success',
  })

  uploadAll(event.data.files, `media/project-${projectId}/files`)
  const results = await waitForAll()
  if (results.fulfilled.length > 0) {
    await saveFiles(projectId, results.fulfilled)
    toast.add({
      title: 'Загрузка файлов завершена',
      color: 'success',
    })
    emit('completed')
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
