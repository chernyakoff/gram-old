<template>
  <div class="relative w-full">
    <!-- Обычный режим -->
    <div v-if="!isFullscreen" class="relative">
      <UTextarea
        :model-value="modelValue"
        @update:model-value="$emit('update:modelValue', $event)"
        :rows="rows"
        :placeholder="placeholder"
        :variant="variant"
        :disabled="disabled"
        :autoresize="autoresize"
        v-bind="$attrs"
      />
      <button
        @click="toggleFullscreen"
        type="button"
        class="absolute top-2 right-2 p-2 rounded-md bg-white dark:bg-gray-800 hover:bg-gray-100 dark:hover:bg-gray-700 border border-gray-300 dark:border-gray-600 transition-colors z-10"
        title="Полноэкранный режим"
      >
        <UIcon name="i-lucide-maximize-2" class="w-2 h-2 text-gray-600 dark:text-gray-400" />
      </button>
    </div>

    <!-- Fullscreen режим -->
    <Teleport to="body">
      <div v-if="isFullscreen" class="fixed inset-0 z-50 bg-white dark:bg-gray-900 flex flex-col">
        <!-- Заголовок -->
        <div
          class="flex items-center justify-between px-6 py-4 border-b border-gray-200 dark:border-gray-700"
        >
          <h2 class="text-lg font-semibold text-gray-900 dark:text-white">{{ fullscreenTitle }}</h2>
          <div class="flex gap-2">
            <button
              @click="toggleFullscreen"
              type="button"
              class="p-2 rounded-md hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
              title="Закрыть"
            >
              <UIcon name="i-lucide-x" class="w-5 h-5 text-gray-600 dark:text-gray-400" />
            </button>
          </div>
        </div>

        <!-- Textarea на весь экран -->
        <div class="flex-1 p-6">
          <UTextarea
            :model-value="modelValue"
            @update:model-value="$emit('update:modelValue', $event)"
            :placeholder="placeholder"
            :variant="variant"
            :disabled="disabled"
            class="w-full h-full"
            :ui="{
              base: 'w-full h-full',
            }"
            autofocus
          />
        </div>

        <!-- Футер с информацией -->
        <div
          class="px-6 py-3 border-t border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800"
        >
          <div class="flex justify-between items-center text-sm text-gray-600 dark:text-gray-400">
            <span>Символов: {{ modelValue?.length || 0 }}</span>
            <span>Строк: {{ (modelValue || '').split('\n').length }}</span>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<script setup lang="ts">
import { onMounted, onUnmounted, ref } from 'vue'

interface Props {
  modelValue?: string
  rows?: number
  placeholder?: string
  variant?: 'outline' | 'soft' | 'subtle' | 'ghost' | 'none'
  disabled?: boolean
  autoresize?: boolean
  fullscreenTitle?: string
}

withDefaults(defineProps<Props>(), {
  rows: 8,
  placeholder: '',
  variant: 'outline',
  disabled: false,
  autoresize: false,
  fullscreenTitle: 'Редактор текста',
})

defineEmits<{
  'update:modelValue': [value: string]
}>()

const isFullscreen = ref(false)

const toggleFullscreen = () => {
  isFullscreen.value = !isFullscreen.value
}

// Закрытие по ESC
onMounted(() => {
  const handleEsc = (e: KeyboardEvent) => {
    if (e.key === 'Escape' && isFullscreen.value) {
      isFullscreen.value = false
    }
  }
  window.addEventListener('keydown', handleEsc)

  onUnmounted(() => {
    window.removeEventListener('keydown', handleEsc)
  })
})
</script>
