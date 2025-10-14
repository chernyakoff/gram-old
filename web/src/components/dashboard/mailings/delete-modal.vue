<template>
  <UModal v-model:open="open" title="Вы уверены?" description="Это действие нельзя будет отменить.">
    <UButton variant="ghost" icon="bx:trash" title="Удалить рассылку" />
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
import { useMailings } from '@/composables/use-mailings'

const emit = defineEmits<{
  (e: 'close'): void
}>()

const { id } = defineProps<{
  id: number
}>()

const open = ref(false)

const { del } = useMailings()

async function onSubmit() {
  await del([id])
  open.value = false
  emit('close')
}
</script>
