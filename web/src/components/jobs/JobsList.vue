<template>
  <div class="overflow-y-auto divide-y divide-default">
    <div
      v-for="(job, index) in jobs"
      :key="index"
      :ref="el => { jobRefs[job.id] = el as Element }">
      <div
        class="p-4 sm:px-6 text-sm cursor-pointer border-l-2 transition-colors"
        :class="[
          selectedJob && selectedJob.id === job.id ? 'border-primary bg-primary/10' : 'border-(--ui-bg) hover:border-primary hover:bg-primary/5'
        ]"
        @click="selectedJob = job">
        <div class="flex items-center justify-between">
          <div class="flex items-center gap-3">
            {{ job.name }}
          </div>
          <span>{{ useDateFormat(job.createdAt, 'HH:MM DD.MM.YY') }}</span>
          <UChip :color="statusColor[job.status]" />
        </div>
      </div>
    </div>
  </div>
</template>
<script setup lang="ts">
import { watch } from 'vue';
import { ref } from 'vue';

import { useDateFormat } from '@vueuse/core'


defineProps<{
  jobs: BackgroundJob[]
}>()

const statusColor = {
  "pending": "neutral",
  "running": "warning",
  "failed": "error",
  "finished": "info",
} as const

const jobRefs = ref<Record<string, Element>>({})

const selectedJob = defineModel<BackgroundJob | null>()


watch(selectedJob, () => {
  if (!selectedJob.value) {
    return
  }
  //Element implicitly has an 'any' type because index expression is not of type 'number'
  const ref = jobRefs.value[selectedJob.value.id]
  if (ref) {
    ref.scrollIntoView({ block: 'nearest' })
  }
})

</script>
