<template>
  <UModal v-model:open="open" title="Фильтр диалогов" :dismissible="false">
    <UButton class="relative" icon="bx:filter-alt" variant="ghost" color="neutral">
      <UBadge
        v-if="activeFiltersCount > 0"
        :label="activeFiltersCount"
        color="primary"
        size="xs"
        class="absolute -top-1 -right-1"
      />
    </UButton>
    <template #body>
      <USelectMenu
        placeholder="Выберите проект"
        v-model="projectId"
        :items="projects"
        class="w-full mb-4"
        value-key="id"
        label-key="name"
      />

      <USelectMenu
        placeholder="Выберите аккаунт"
        v-model="accountId"
        :items="accounts"
        class="w-full mb-4"
        value-key="id"
        label-key="name"
      />

      <USelectMenu
        placeholder="Выберите рассылку"
        v-model="mailingId"
        :items="mailings"
        class="w-full mb-4"
        value-key="id"
        label-key="name"
      />
    </template>
    <template #footer>
      <div class="flex justify-end gap-2">
        <UButton label="Отмена" color="neutral" variant="subtle" @click="open = false" />
        <UButton label="Сбросить" color="warning" @click="onReset" />
        <UButton label="Применить" color="primary" variant="solid" loading-auto @click="onSubmit" />
      </div>
    </template>
  </UModal>
</template>

<script setup lang="ts">
import type { AccountListOut, MailingListOut, ProjectBase, DialogIn } from '@/types/openapi'
import { computed, onMounted, ref } from 'vue'
import { useAccounts } from '@/composables/use-accounts'
import { useMailings } from '@/composables/use-mailings'
import { useProjects } from '@/composables/use-projects'

const emit = defineEmits<{
  apply: [payload: DialogIn]
  reset: []
}>()

const { list: getProjectList } = useProjects()
const { list: getMailingList } = useMailings()
const { list: getAccountList } = useAccounts()

const projectId = ref<number | undefined>(undefined)
const accountId = ref<number | undefined>(undefined)
const mailingId = ref<number | undefined>(undefined)

const projects = ref<ProjectBase[]>([])
const mailings = ref<MailingListOut[]>([])
const accounts = ref<AccountListOut[]>([])

// Вычисляемые свойства для индикации активных фильтров
/* const hasActiveFilters = computed(() => {
  return (
    projectId.value !== undefined || accountId.value !== undefined || mailingId.value !== undefined
  )
}) */

const activeFiltersCount = computed(() => {
  let count = 0
  if (projectId.value !== undefined) count++
  if (accountId.value !== undefined) count++
  if (mailingId.value !== undefined) count++
  return count
})

onMounted(async () => {
  projects.value = await getProjectList()
  mailings.value = await getMailingList()
  accounts.value = await getAccountList()
})

const open = ref(false)

function onSubmit() {
  const payload: DialogIn = {
    projectId: projectId.value ?? null, // конвертируем undefined в null для API
    accountId: accountId.value ?? null,
    mailingId: mailingId.value ?? null,
  }

  emit('apply', payload)
  open.value = false
}

function onReset() {
  projectId.value = undefined
  accountId.value = undefined
  mailingId.value = undefined

  const payload: DialogIn = {
    projectId: null,
    accountId: null,
    mailingId: null,
  }

  emit('reset')
  emit('apply', payload)
  open.value = false
}
</script>
