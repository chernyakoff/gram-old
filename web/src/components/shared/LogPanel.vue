<template>
  <div v-if="visible || modelValue.length" class="flex flex-col h-64 p-2 rounded border">
    <div ref="logContainer" @scroll="onScroll" class="flex-1 overflow-auto space-y-1 mb-2">
      <div v-for="(log, index) in modelValue" :key="index" class="text-xs font-mono flex items-start gap-2">
        <span v-if="log.status === 'info'">💡</span>
        <span v-else-if="log.status === 'error'">🚫</span>
        <span v-else-if="log.status === 'success'">✅</span>
        <span v-else-if="log.status === 'warning'">⚠️</span>
        <span>{{ log.message }}</span>
      </div>
    </div>
  </div>
</template>
<script setup lang="ts">
import { ref, watch, nextTick, defineProps } from 'vue'


const props = defineProps<{
  visible: boolean
  modelValue: LogEntry[]
}>()


const logContainer = ref<HTMLElement | null>(null)
const isAtBottom = ref(true)

function checkIfAtBottom () {
  if (!logContainer.value) return
  const el = logContainer.value
  isAtBottom.value = el.scrollHeight - el.scrollTop - el.clientHeight < 5
}

function scrollToBottom () {
  if (!logContainer.value || !isAtBottom.value) return
  requestAnimationFrame(() => {
    logContainer.value!.scrollTop = logContainer.value!.scrollHeight
  })
}

function onScroll () {
  checkIfAtBottom()
}

// Автопрокрутка при изменении логов
watch(
  () => props.modelValue,
  () => nextTick(scrollToBottom),
  { deep: true }
)
</script>
