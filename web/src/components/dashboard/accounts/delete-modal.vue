<template>
  <UModal
    v-model:open="open"
    :title="`Удаление ${selectedIds.length} ${plur(selectedIds.length)}`"
    :description="`Вы уверены? Это действие нельзя будет отменить.`"
  >
    <UButton
      v-if="selectedIds.length"
      label="Удалить"
      color="error"
      variant="subtle"
      icon="bx:trash"
    >
      <template #trailing>
        <UKbd>
          {{ selectedIds.length }}
        </UKbd>
      </template>
    </UButton>
    <template #body>
      <div class="flex justify-end gap-2">
        <UButton label="Отмена" color="neutral" variant="subtle" @click="open = false" />
        <UButton label="Удалить" color="error" variant="solid" loading-auto @click="onSubmit" />
      </div>
    </template>
  </UModal>
</template>
<script setup lang="ts">
import { ref } from 'vue'
import { useAccounts } from '@/composables/use-accounts'
import { pluralize } from '@/utils/pluralize'

const emit = defineEmits<{
  (e: 'close'): void
}>()

const { selectedIds } = defineProps<{
  selectedIds: number[]
}>()

const open = ref(false)

const plur = (n: number): string => {
  return pluralize(n, ['аккаунта', 'аккаунтов', 'аккаунтов'])
}

const { del } = useAccounts()

async function onSubmit() {
  await del(selectedIds)
  open.value = false
  emit('close')
}
</script>
