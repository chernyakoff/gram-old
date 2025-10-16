<template>
  <UModal v-model:open="open" title="Добавление рассылки">
    <UButton label="Добавить рассылку" icon="bx:bxs-plus-circle" />

    <template #body>
      <UForm ref="form" :schema="mailingFormSchema" :state="state" @submit="onSubmit">
        <UFormField name="name" label="Название рассылки" class="mb-4">
          <UInput v-model="state.name" :items="projects" class="w-full" />
        </UFormField>
        <UFormField name="projectId" label="Выберите проект" class="mb-4">
          <USelectMenu
            v-model="state.projectId"
            :items="projects"
            class="w-full"
            value-key="value"
          />
        </UFormField>
        <UTabs :items="tabItems" variant="link" :ui="{ trigger: 'grow' }" class="gap-4 w-full">
          <template #text>
            <div class="tab-panel">
              <UFormField name="text">
                <UTextarea
                  v-model="state.text"
                  placeholder="@username1&#10;@username2"
                  class="w-full h-full resize-none"
                  :rows="9"
                />
              </UFormField>
            </div>
          </template>

          <template #file>
            <div class="tab-panel">
              <UFormField name="file" class="">
                <UFileUpload
                  v-model="state.file"
                  class="w-full h-full min-h-48"
                  label="Загрузите файл"
                  description="TXT (до 1MB)"
                />
              </UFormField>
            </div>
          </template>
        </UTabs>
      </UForm>
    </template>
    <template #footer="{ close }">
      <div class="flex justify-end gap-2 w-full">
        <UButton label="Отмена" color="neutral" variant="outline" @click="close" />
        <UButton label="Отправить" @click="doSubmit" />
      </div>
    </template>
  </UModal>
</template>

<script setup lang="ts">
import { reactive, ref, useTemplateRef, watch } from 'vue'
import { useMailings } from '@/composables/use-mailings'
import type { FormSubmitEvent, SelectMenuItem, TabsItem } from '@nuxt/ui'
import { mailingFormSchema, mailingInSchema, type MailingFormSchema } from '@/schemas/mailings'
import { useProjects } from '@/composables/use-projects'

import { parseAsync, ValiError, summarize as summarizeErrors } from 'valibot'
import type { MailingIn } from '@/types/openapi'

const tabItems = [
  {
    label: 'Список',
    icon: 'i-lucide-list', // или 'running'
    slot: 'text' as const,
  },
  {
    label: 'Файл',
    icon: 'i-lucide-file',
    slot: 'file' as const,
  },
] satisfies TabsItem[]

const toast = useToast()
const { create } = useMailings()

const open = defineModel<boolean>('open', { default: false })
const form = useTemplateRef('form')
const { list: getList } = useProjects()
const projects = ref<SelectMenuItem[]>([])

const emit = defineEmits<{
  (e: 'close'): void
}>()

const getEmptyState = (): MailingFormSchema => ({
  projectId: undefined,
  name: '',
  file: undefined,
  text: undefined,
})

watch(
  open,
  async (open) => {
    if (open) {
      Object.assign(state, getEmptyState())
      if (projects.value.length === 0) {
        const list = await getList()
        projects.value = list.map((m) => ({
          label: m.name,
          value: m.id,
        })) as SelectMenuItem[]
      }
    }
  },
  { immediate: true },
)

const state = reactive<MailingFormSchema>(getEmptyState())

const doSubmit = async () => {
  await form.value?.submit()
}

const onSubmit = async (event: FormSubmitEvent<MailingFormSchema>) => {
  try {
    const result = (await parseAsync(mailingInSchema, event.data)) satisfies MailingIn
    await create(result)
    open.value = false
    emit('close')
  } catch (error) {
    if (error instanceof ValiError) {
      console.error('Validation errors:', error.issues)
      toast.add({
        title: 'Ошибка',
        description: summarizeErrors(error.issues),
        color: 'error',
      })
    } else {
      console.error('An unexpected error occurred:', error)
    }
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
