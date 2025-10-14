<template>
  <UModal
    v-model:open="open"
    :title="`Назначение в проект`"
    :description="`Будет назначено ${selectedIds.length} ${plur(selectedIds.length)}.`"
  >
    <UButton
      v-if="selectedIds.length"
      label="Назначить в проект"
      color="neutral"
      variant="subtle"
      icon="bx:link"
    >
      <template #trailing>
        <UKbd>
          {{ selectedIds.length }}
        </UKbd>
      </template>
    </UButton>
    <template #body>
      <UFormField name="projectId" label="Выберите проект" :error="error">
        <USelectMenu v-model="projectId" :items="projects" class="w-full" value-key="value" />
      </UFormField>
    </template>
    <template #footer>
      <div class="flex justify-end gap-2">
        <UButton label="Отмена" color="neutral" variant="subtle" @click="open = false" />
        <UButton label="Назначить" color="primary" variant="solid" loading-auto @click="onSubmit" />
      </div>
    </template>
  </UModal>
</template>
<script setup lang="ts">
import { ref, watch } from 'vue'
import { useProjects } from '@/composables/use-projects'
import type { SelectMenuItem } from '@nuxt/ui'
import { pluralize } from '@/utils/pluralize'
import { useAccounts } from '@/composables/use-accounts'
import type { BindProjectIn } from '@/types/openapi'

const emit = defineEmits<{
  (e: 'close'): void
}>()

const projectId = ref()

const { selectedIds } = defineProps<{
  selectedIds: number[]
}>()

const open = defineModel<boolean>('open', { default: false })
const error = ref<string | undefined>(undefined)

const plur = (n: number): string => {
  return pluralize(n, ['аккаунт', 'аккаунта', 'аккаунтов'])
}

const { list: getList } = useProjects()
const { bindProject } = useAccounts()
const projects = ref<SelectMenuItem[]>([])

watch(
  open,
  async (open) => {
    if (open) {
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

async function onSubmit() {
  if (!projectId.value) {
    error.value = 'Пожалуйста, выберите проект'
    return
  }

  error.value = undefined

  const data: BindProjectIn = {
    projectId: projectId.value,
    accountIds: selectedIds,
  }

  await bindProject(data)
  open.value = false
  emit('close')
}
</script>
