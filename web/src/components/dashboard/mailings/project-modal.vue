<template>
  <UModal v-model:open="open" title="Перенос">
    <template #body>
      <UFormField name="projectId" label="Выберите проект" :error="error">
        <USelectMenu v-model="projectId" :items="projects" class="w-full" value-key="value" />
      </UFormField>
      <p v-if="selectedProjectName" class="mt-3 text-sm text-muted">
        Будет создана новая рассылка с неотправленными ({{ props.pendingCount }}) пользователями в проекте «{{ selectedProjectName }}».
      </p>
    </template>
    <template #footer>
      <div class="flex justify-end gap-2 w-full">
        <UButton label="Отменить" color="neutral" variant="outline" @click="open = false" />
        <UButton label="Перенести" loading-auto @click="onSubmit" />
      </div>
    </template>
  </UModal>
</template>

<script setup lang="ts">
import type { SelectMenuItem } from '@nuxt/ui'
import { computed, ref, watch } from 'vue'

import { useMailings } from '@/composables/use-mailings'
import { useProjects } from '@/composables/use-projects'

const emit = defineEmits<{
  (e: 'close'): void
}>()

const props = defineProps<{
  mailingId?: number
  currentProjectId?: number
  pendingCount?: number
}>()

const open = defineModel<boolean>('open', { default: false })
const projectId = ref<number>()
const error = ref<string | undefined>(undefined)

const { list: getProjects } = useProjects()
const { changeProject } = useMailings()
const allProjects = ref<SelectMenuItem[]>([])
const projects = computed(() =>
  allProjects.value.filter((item) => item.value !== props.currentProjectId),
)
const selectedProjectName = computed(() => {
  const selected = projects.value.find((item) => item.value === projectId.value)
  return selected?.label
})

watch(
  open,
  async (isOpen) => {
    if (!isOpen) {
      return
    }

    projectId.value = undefined
    error.value = undefined

    if (allProjects.value.length === 0) {
      const list = await getProjects()
      allProjects.value = list.map((item) => ({
        label: item.name,
        value: item.id,
      })) as SelectMenuItem[]
    }
  },
  { immediate: true },
)

async function onSubmit() {
  if (!projectId.value) {
    error.value = 'Пожалуйста, выберите проект'
    return
  }

  if (!props.mailingId) {
    error.value = 'Не выбрана рассылка'
    return
  }

  error.value = undefined

  await changeProject({
    mailingId: props.mailingId,
    projectId: projectId.value,
  })

  open.value = false
  emit('close')
}
</script>
