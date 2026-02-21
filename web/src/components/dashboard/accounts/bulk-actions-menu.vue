<template>
  <div v-if="selectedIds.length" class="flex items-center">
    <UDropdownMenu :items="items" :content="{ align: 'end' }">
      <UButton
        :label="`Действия (${selectedIds.length})`"
        color="neutral"
        variant="subtle"
        trailing-icon="i-lucide-chevron-down" />
    </UDropdownMenu>
  </div>
  <SetLimitModal
    v-model:open="openLimit"
    :selected-ids="selectedIds"
    hide-trigger
    @close="emit('completed')" />
  <CheckModal
    v-model:open="openCheck"
    :selected-ids="selectedIds"
    hide-trigger
    @completed="emit('completed')" />
  <GenerateModal
    v-model:open="openGenerate"
    :selected-ids="selectedIds"
    hide-trigger
    @completed="emit('completed')" />
  <BindProjectModal
    v-model:open="openBindProject"
    :selected-ids="selectedIds"
    hide-trigger
    @close="emit('completed')" />
  <DeleteAccountsModal
    v-model:open="openDelete"
    :selected-ids="selectedIds"
    hide-trigger
    @close="emit('completed')" />
</template>
<script setup lang="ts">
import { computed, ref } from 'vue'
import type { DropdownMenuItem } from '@nuxt/ui'

import SetLimitModal from '@/components/dashboard/accounts/limit-modal.vue'
import CheckModal from '@/components/dashboard/accounts/check-modal.vue'
import GenerateModal from '@/components/dashboard/accounts/generate-modal.vue'
import BindProjectModal from '@/components/dashboard/accounts/project-modal.vue'
import DeleteAccountsModal from '@/components/dashboard/accounts/delete-modal.vue'

const { selectedIds } = defineProps<{
  selectedIds: number[]
}>()

const emit = defineEmits<{
  (e: 'completed'): void
}>()

const openLimit = ref(false)
const openCheck = ref(false)
const openGenerate = ref(false)
const openBindProject = ref(false)
const openDelete = ref(false)

const items = computed<DropdownMenuItem[][]>(() => [
  [
    {
      label: 'Проверить аккаунты',
      icon: 'bx:search-alt',
      onSelect: () => {
        openCheck.value = true
      },
    },
    {
      label: 'Генератор',
      icon: 'oui:generate',
      onSelect: () => {
        openGenerate.value = true
      },
    },
    {
      label: 'Установить лимит',
      icon: 'ix:lower-limit',
      onSelect: () => {
        openLimit.value = true
      },
    },
    {
      label: 'Назначить в проект',
      icon: 'bx:link',
      onSelect: () => {
        openBindProject.value = true
      },
    },
  ],
  [
    {
      label: 'Удалить',
      icon: 'bx:trash',
      color: 'error',
      onSelect: () => {
        openDelete.value = true
      },
    },
  ],
])
</script>
