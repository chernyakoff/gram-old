<template>
  <UModal v-model:open="open" title="Редактирование файла" :description="file.filename">
    <template #body>
      <UForm ref="form" :schema="editFileSchema" :state="state" @submit="onSubmit">
        <UFormField name="status" label="Статус" class="mb-4">
          <USelect
            v-model="state.status"
            :items="statusOptions"
            placeholder="Выберите статус"
            value-key="value"
          />
        </UFormField>
        <UFormField name="title" label="Описание" class="mb-4">
          <UTextarea :rows="3" v-model="state.title" size="md" class="w-full" />
        </UFormField>
        <UFormField name="filename" label="Имя файла" class="mb-4">
          <UInput v-model="state.filename" size="md" class="w-full" />
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
import { useProjects } from '@/composables/use-projects'
import type { ProjectFileOut } from '@/types/openapi'
import type { FormSubmitEvent } from '@nuxt/ui'
import * as v from 'valibot'
import { reactive } from 'vue'

const { file, projectId } = defineProps<{ file: ProjectFileOut; projectId: number }>()

const { updateFile } = useProjects()

const open = defineModel<boolean>({ default: false })

const emit = defineEmits<{
  (e: 'close'): void
}>()

const editFileSchema = v.object({
  title: v.pipe(
    v.string(),
    v.nonEmpty('обязательное поле'),
    v.minLength(4, 'должно содержать не менее 4 символов'),
    v.maxLength(256, 'должно содержать не более 64 символов'),
  ),
  filename: v.pipe(
    v.string(),
    v.nonEmpty('обязательное поле'),
    v.minLength(4, 'должно содержать не менее 4 символов'),
    v.maxLength(64, 'должно содержать не более 64 символов'),
  ),
  status: v.nullish(v.picklist(['engage', 'offer', 'closing', 'complete'], 'некорректный статус')),
})

const statusOptions = [
  { value: undefined, label: 'Не выбрано' }, // или { value: null, label: '—' }
  { value: 'engage', label: 'ENGAGE' },
  { value: 'offer', label: 'OFFER' },
  { value: 'closing', label: 'CLOSING' },
  { value: 'complete', label: 'COMPLETE' },
]

type EditFileSchema = v.InferOutput<typeof editFileSchema>

const state = reactive({
  title: file.title,
  filename: file.filename,
  status: file.status, // может быть undefined
})

const onSubmit = async (event: FormSubmitEvent<EditFileSchema>) => {
  open.value = false
  await updateFile(projectId, file.id, event.data)

  emit('close')
}
</script>
