<template>
  <div class="flex-1 overflow-auto space-y-1 mb-2 p-8">
    <div
      v-for="(log, index) in job.logs"
      :key="index"
      class="text-xs font-mono flex items-start gap-2"
    >
      <span v-if="log.status === 'info'">💡</span>
      <span v-else-if="log.status === 'error'">🚫</span>
      <span v-else-if="log.status === 'success'">✅</span>
      <span v-else-if="log.status === 'warning'">⚠️</span>
      <span>{{ log.message }}</span>
    </div>
  </div>
</template>
<script setup lang="ts">
  const { job } = defineProps<{
    job: BackgroundJob
  }>()
</script>
