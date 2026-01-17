<template>
  <UDashboardPanel>
    <template #header>
      <UDashboardNavbar title="Файлы проекта" :ui="{ right: 'gap-3' }">
        <template #leading>
          <UDashboardSidebarCollapse />
        </template>
        <template #right>
          <UButton
            size="lg"
            label="Назад"
            variant="outline"
            color="neutral"
            @click="$router.back()"
          />
        </template>
      </UDashboardNavbar>
    </template>
    <template #body>
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
  </UDashboardPanel>
</template>
<script setup lang="ts">
import { useBackgroundJobs } from '@/stores/jobs-store'
import { useUploadStore } from '@/stores/upload-store'
import { reactive, ref, watch } from 'vue'
import type { FormSubmitEvent, TabsItem } from '@nuxt/ui'
import { textFilesArraySchema, type TextFilesArraySchema } from '@/schemas/project-files'
import type { ProjectFilesIn } from '@/types/openapi'
import { useProjects } from '@/composables/use-projects'

const props = defineProps<{ id?: string }>()
const projectId = props.id ? Number(props.id) : undefined

const { uploadFiles } = useProjects()

const { uploadAll, waitForAll } = useUploadStore()
const jobsStore = useBackgroundJobs()

const state = reactive<TextFilesArraySchema>({
  files: [],
})

const tabs = [
  { label: 'Файлы', icon: 'bx:file', slot: 'files' as const },
  { label: 'Загрузка', icon: 'bx:upload', slot: 'upload' as const },
] satisfies TabsItem[]

const onSubmit = async (event: FormSubmitEvent<TextFilesArraySchema>) => {
  if (projectId === undefined) {
    throw new Error('Project ID is required')
  }
  uploadAll(event.data.files, `media/projects/${projectId}`)
  const results = await waitForAll()

  const payload: ProjectFilesIn = {
    projectId, //Type 'number | undefined' is not assignable to type 'number'.
    files: results.fulfilled,
  }
  const { id } = uploadFiles(payload)

  // lfjnu
  console.log(event)
}
</script>
