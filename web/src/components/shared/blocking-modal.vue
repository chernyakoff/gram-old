<template>
  <UModal :dismissible="false" v-model:open="open">
    <template #header>
      <div class="flex items-center gap-3">
        <UIcon name="i-heroicons-arrow-path" class="w-6 h-6 animate-spin text-primary" />
        <h3 class="text-lg font-semibold">{{ title }}</h3>
      </div>
    </template>
    <template #body>
      <div class="space-y-2 text-sm text-muted">
        {{ text }}
      </div>
    </template>
  </UModal>
</template>

<script setup lang="ts">
defineProps<{
  title?: string
  text?: string
}>()

const open = defineModel<boolean>('open', { default: false })
</script>
