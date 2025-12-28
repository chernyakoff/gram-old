<template>
  <UPopover :dismissible="false" v-model:open="open" :ui="{ content: 'w-24' }">
    <template #anchor>
      <UInput
        ref="inputRef"
        :model-value="modelValue"
        placeholder="00:00"
        class="w-24"
        @update:model-value="$emit('update:modelValue', $event)"
        @focus="open = true"
        @blur="
          () => {
            open = false
            $emit('blur')
          }
        "
      />
    </template>
    <template #content>
      <div class="max-h-60 overflow-y-auto py-1">
        <div
          v-for="time in timeOptions"
          :key="time"
          role="button"
          class="w-full text-left px-2 py-1.5 text-sm hover:bg-gray-100 dark:hover:bg-gray-800 rounded cursor-pointer"
          @mousedown="
            () => {
              $emit('update:modelValue', time)
              $emit('change', time)
              open = false
              inputRef?.input?.blur()
            }
          "
        >
          {{ time }}
        </div>
      </div>
    </template>
  </UPopover>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'

defineProps<{
  modelValue: string
}>()

defineEmits<{
  'update:modelValue': [value: string]
  change: [value: string]
  blur: []
}>()

const open = ref(false)
const inputRef = ref()

// Генерация временных слотов с шагом 15 минут
const timeOptions = computed(() => {
  const options: string[] = []
  for (let h = 0; h < 24; h++) {
    for (let m = 0; m < 60; m += 15) {
      const hour = String(h).padStart(2, '0')
      const minute = String(m).padStart(2, '0')
      options.push(`${hour}:${minute}`)
    }
  }
  return options
})
</script>
