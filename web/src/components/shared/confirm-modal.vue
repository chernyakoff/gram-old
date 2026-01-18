<template>
  <UModal v-model:open="open" :title="title" :description="description">
    <template #footer>
      <div class="flex justify-end gap-3">
        <UButton :color="cancelButton.color || 'gray'" variant="ghost" @click="cancel">
          {{ cancelButton.label || 'Отмена' }}
        </UButton>
        <UButton :color="confirmButton.color || 'error'" @click="confirm">
          {{ confirmButton.label || 'Подтвердить' }}
        </UButton>
      </div>
    </template>
  </UModal>
</template>

<script setup lang="ts">
interface ConfirmButton {
  label?: string
  color?: string
}

interface Props {
  title?: string
  description?: string
  confirmButton?: ConfirmButton
  cancelButton?: ConfirmButton
}

withDefaults(defineProps<Props>(), {
  title: 'Подтверждение',
  description: 'Вы уверены?',
  confirmButton: () => ({ label: 'Подтвердить', color: 'error' }),
  cancelButton: () => ({ label: 'Отмена', color: 'gray' }),
})

const open = defineModel<boolean>({ default: false })

const emit = defineEmits<{
  confirm: []
  cancel: []
}>()

function confirm() {
  emit('confirm')
  open.value = false
}

function cancel() {
  emit('cancel')
  open.value = false
}
</script>
