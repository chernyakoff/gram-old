<template>
  <UDrawer direction="right" :title="title" class="w-160" :handle="false" v-model:open="open">
    <template #body>
      <UForm ref="form" :schema="projectInSchema" :state="state" @submit="onSubmit">
        <UFormField label="Наименование" name="name" class="mb-4">
          <UInput v-model="state.name" size="md" class="w-full" />
        </UFormField>

        <UFormField label="Описание" name="description" class="mb-4">
          <UTextarea v-model="state.description" class="w-full" :rows="3" />
        </UFormField>
      </UForm>
    </template>
    <template #footer>
      <UButton
        label="Сохранить"
        :disabled="!form?.dirty"
        @click="doSubmit"
        color="neutral"
        class="justify-center"
      />
      <UButton
        label="Закрыть"
        color="neutral"
        variant="outline"
        class="justify-center"
        @click="$emit('update:open', false)"
      />
    </template>
  </UDrawer>
</template>
<script setup lang="ts">
import { useProjects } from '@/composables/use-projects'
import { projectInSchema, type ProjectInSchema } from '@/schemas/projects'
import type { ProjectIn } from '@/types/openapi'
import type { FormSubmitEvent } from '@nuxt/ui'
import { useTemplateRef } from 'vue'
import * as v from 'valibot'
import { reactive, watch, computed } from 'vue'

const open = defineModel<boolean>('open', { default: false })
const form = useTemplateRef('form')
const title = computed(() => (projectId ? `Редактировать` : 'Создать'))

const { projectId } = defineProps<{
  projectId?: number
}>()

const emit = defineEmits<{
  (e: 'update:open', value: boolean): void
  (e: 'closed'): void
}>()

const getEmptyState = (): ProjectInSchema => ({
  name: '',
  description: '',
})

const state = reactive<ProjectInSchema>(getEmptyState())

const { get, create, update } = useProjects()

const doSubmit = async () => {
  await form.value?.submit()
}

const onSubmit = async (event: FormSubmitEvent<ProjectInSchema>) => {
  const data = event.data satisfies ProjectIn
  if (!projectId) {
    await create(data)
  } else {
    await update(projectId, data)
  }
  open.value = false
  emit('closed')
}

watch(
  [open, () => projectId],
  async ([isOpen, id]) => {
    let data: ProjectInSchema
    if (isOpen && id) {
      const dto = await get(id)
      data = v.parse(projectInSchema, dto)
    } else {
      data = getEmptyState()
    }
    Object.assign(state, data)
  },
  { immediate: true },
)
</script>
