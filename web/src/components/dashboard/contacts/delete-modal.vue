<template>
  <UModal
    v-model:open="open"
    :title="`Удалить ${selectedIds.length} контактов`"
    :description="`Вы уверены? Это действие нельзя будет отменить.`"
  >
    <UButton
      v-if="selectedIds.length"
      label="Удалить"
      color="error"
      variant="subtle"
      icon="i-lucide-trash"
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
import { useContacts } from '@/composables/use-mailings'

const emit = defineEmits<{
  (e: 'close'): void
}>()

const { selectedIds } = defineProps<{
  selectedIds: number[]
}>()

const open = ref(false)

const { del } = useContacts()

async function onSubmit() {
  await del(selectedIds)
  open.value = false
  emit('close')
}
</script>
