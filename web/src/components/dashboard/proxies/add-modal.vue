<template>
  <UModal v-model:open="open" title="Загрузка прокси" description="socks5">
    <UButton label="Добавить" icon="i-lucide-plus" />
    <template #body>
      <UForm ref="form" :schema="proixiesBulkCreateForm" :state="state" @submit="onSubmit">
        <UTabs :items="tabItems" variant="link" :ui="{ trigger: 'grow' }" class="gap-4 w-full">
          <template #text>
            <div class="tab-panel">
              <UFormField name="text">
                <UTextarea
                  v-model="state.text"
                  placeholder="ip:port:login:pass&#10;ip:port:login:pass"
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
                  description="TXT (до 1 MB)"
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
import { reactive, useTemplateRef, watch } from 'vue'
import type { FormSubmitEvent, TabsItem } from '@nuxt/ui'
import { useProxies } from '@/composables/use-proxies'
import { useBackgroundJobs } from '@/stores/jobs-store'

import {
  proixiesBulkCreateSchema,
  proixiesBulkCreateForm,
  type ProixiesBulkCreateForm,
} from '@/schemas/proxies'
import type { ProxiesBulkCreateIn } from '@/types/openapi'
import { parseAsync, ValiError, summarize as summarizeErrors } from 'valibot'
const emit = defineEmits<{
  (e: 'close'): void
  (e: 'completed'): void
}>()

const open = defineModel<boolean>('open', { default: false })
const form = useTemplateRef('form')

const toast = useToast()

const { upload } = useProxies()

const jobsStore = useBackgroundJobs()

const tabItems = [
  {
    label: 'Списком',
    icon: 'i-lucide-list', // или 'running'
    slot: 'text' as const,
  },
  {
    label: 'Файлом',
    icon: 'i-lucide-file',
    slot: 'file' as const,
  },
] satisfies TabsItem[]

const getEmptyState = (): ProixiesBulkCreateForm => ({
  file: undefined,
  text: undefined,
})

const state = reactive<ProixiesBulkCreateForm>(getEmptyState())

watch(
  open,
  async (open) => {
    if (open) {
      Object.assign(state, getEmptyState())
    }
  },
  { immediate: true },
)

const doSubmit = async () => {
  await form.value?.submit()
}

const onSubmit = async (event: FormSubmitEvent<ProixiesBulkCreateForm>) => {
  try {
    const data = (await parseAsync(
      proixiesBulkCreateSchema,
      event.data,
    )) satisfies ProxiesBulkCreateIn
    const { id } = await upload(data)
    open.value = false
    emit('close')
    toast.add({
      title: 'Загрузка прокси начата',
      description: `Можно посмотреть ход выполнения в разделе «задачи»`,
      color: 'success',
    })
    jobsStore.add({
      id,
      name: 'Загрузка прокси',
      onComplete: () => emit('completed'),
    })
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
