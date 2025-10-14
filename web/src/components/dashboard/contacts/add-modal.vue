<template>
  <UModal v-model:open="open" title="Добавление контактов">
    <UButton label="Добавить" icon="i-lucide-plus" />
    <template #description>
      <span class="text-xs text-muted italic">
        каждый с новой строки, в формате
        <span class="text-black dark:text-white">username</span>
        или
        <span class="text-black dark:text-white">@username</span>
      </span>
    </template>
    <template #body>
      <UForm ref="form" :schema="contactsBulkCreateFormSchema" :state="state" @submit="onSubmit">
        <UFormField name="projectId" label="Выберите проект">
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
                  description="TXT (maкс. 1MB)"
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
import { useContacts } from '@/composables/use-mailings'
import type { FormSubmitEvent, SelectMenuItem, TabsItem } from '@nuxt/ui'
import {
  contactsBulkCreateFormSchema,
  contactsBulkCreateInSchema,
  type ContactsBulkCreateFormSchema,
} from '@/schemas/contacts'
import { useProjects } from '@/composables/use-projects'

import { parseAsync, ValiError, summarize as summarizeErrors } from 'valibot'
import type { ContactsBulkCreateIn } from '@/types/openapi'

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
const { create } = useContacts()

const open = defineModel<boolean>('open', { default: false })
const form = useTemplateRef('form')
const { list: getList } = useProjects()
const projects = ref<SelectMenuItem[]>([])

const emit = defineEmits<{
  (e: 'close'): void
}>()

const getEmptyState = (): ContactsBulkCreateFormSchema => ({
  projectId: undefined,
  file: undefined,
  text: undefined,
})

watch(
  open,
  async (open) => {
    if (open) {
      Object.assign(state, getEmptyState())
      if (projects.value.length === 0) {
        projects.value = (await getList()).map((m) => ({
          label: m.name,
          value: m.id,
        }))
      }
    }
  },
  { immediate: true },
)

const state = reactive<ContactsBulkCreateFormSchema>(getEmptyState())

const doSubmit = async () => {
  await form.value?.submit()
}

const onSubmit = async (event: FormSubmitEvent<ContactsBulkCreateFormSchema>) => {
  try {
    const result = (await parseAsync(
      contactsBulkCreateInSchema,
      event.data,
    )) satisfies ContactsBulkCreateIn
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
