<template>
  <UModal v-model:open="open" title="Создание проекта">
    <UButton label="Добавить проект" icon="bx:bxs-plus-circle" />
    <template #body>
      <UForm ref="form" :schema="projectCreateSchema" :state="state" @submit="onSubmit">
        <UFormField name="name" label="Название проекта">
          <UInput v-model="state.name" size="md" class="w-full" />
        </UFormField>
      </UForm>
    </template>
    <template #footer="{ close }">
      <div class="flex justify-end gap-2 w-full">
        <UButton label="Отмена" color="neutral" variant="subtle" @click="close" />
        <UButton label="Создать" variant="solid" @click="doSubmit" />
      </div>
    </template>
  </UModal>
</template>
<script setup lang="ts">
import { reactive, ref, useTemplateRef } from 'vue'
import { useProjects } from '@/composables/use-projects'
import * as v from 'valibot'
import type { FormSubmitEvent } from '@nuxt/ui'

const form = useTemplateRef('form')

const doSubmit = async () => {
  await form.value?.submit()
}

const projectCreateSchema = v.object({
  name: v.pipe(
    v.string(),
    v.nonEmpty('обязательное поле'),
    v.minLength(4, 'должно содержать не менее 4 символов'),
    v.maxLength(64, 'должно содержать не более 64 символов'),
  ),
})

type ProjectCreateSchema = v.InferOutput<typeof projectCreateSchema>

const emit = defineEmits<{
  (e: 'close'): void
}>()

const state = reactive<ProjectCreateSchema>({
  name: '',
})

const open = ref(false)

const { createProject } = useProjects()

const onSubmit = async (event: FormSubmitEvent<ProjectCreateSchema>) => {
  open.value = false
  await createProject(event.data)
  emit('close')
}
</script>
