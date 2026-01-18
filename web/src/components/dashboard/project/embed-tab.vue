<template>
  <div class="w-full max-w-4xl mx-auto md:min-w-[800px] px-4">
    <UTabs :items="tabs" variant="link" :ui="{ trigger: 'grow' }" class="gap-4">
      <template #files></template>
      <template #upload>
        <div class="mx-auto w-max space-y-4 px-4">
          <UForm ref="form" :schema="textFilesArraySchema" :state="state" @submit="onSubmit">
            <UFileUpload
              v-model="state.files"
              multiple
              accept="text/*"
              layout="list"
              label="Загрузите текстовые файлы"
              description="TXT, MD, CSV и другие текстовые форматы"
              class="w-96 min-h-48 mb-4"
            />
            <UButton
              label="Начать загрузку"
              :disabled="state.files.length < 1"
              color="neutral"
              class="justify-center"
              type="submit"
            />
          </UForm>
        </div>
      </template>
    </UTabs>
  </div>
</template>
<script lang="ts" setup>
import { useBackgroundJobs } from '@/stores/jobs-store'
import { useUploadStore } from '@/stores/upload-store'
import { reactive } from 'vue'
import type { FormSubmitEvent, TabsItem } from '@nuxt/ui'
import { textFilesArraySchema, type TextFilesArraySchema } from '@/schemas/project-files'
import type { ProjectFilesIn } from '@/types/openapi'
import { useProjects } from '@/composables/use-projects'

const { projectId } = defineProps<{
  projectId: number
}>()

const { uploadEmbed } = useProjects()

const { uploadAll, waitForAll } = useUploadStore()
const jobsStore = useBackgroundJobs()

const state = reactive<TextFilesArraySchema>({
  files: [],
})

const toast = useToast()

const tabs = [
  { label: 'Документы', icon: 'bx:file', slot: 'files' as const },
  { label: 'Загрузка', icon: 'bx:upload', slot: 'upload' as const },
] satisfies TabsItem[]

const onSubmit = async (event: FormSubmitEvent<TextFilesArraySchema>) => {
  uploadAll(event.data.files, `media/embed/${projectId}`)
  const results = await waitForAll()
  const s3paths = results.fulfilled.map((f) => f.storagePath)
  const payload: ProjectFilesIn = {
    projectId,
    files: s3paths,
  }
  const res = await uploadEmbed(payload)
  jobsStore.add({
    id: res.id,
    name: 'Сохранение документов',
    onComplete: () => {
      toast.add({
        title: 'Сохранение документов',
        description:
          'Сохранение документов запущено. Ход выполнения можно посмотреть в разделе задачи',
        color: 'success',
      })
    },
  })
}
</script>
