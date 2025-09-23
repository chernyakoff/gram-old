<template>
  <UDashboardPanel id="logs" :default-size="25" :min-size="20" :max-size="30" resizable>
    <UDashboardNavbar :title="title">
      <template #leading>
        <UDashboardSidebarCollapse />
      </template>
      <template #trailing>
        <UBadge :label="filteredJobs.length" variant="subtle" />
      </template>
      <template #right>
        <USelect
          v-model="statusFilter"
          :items="statuses"
          :ui="{
            trailingIcon: 'group-data-[state=open]:rotate-180 transition-transform duration-200',
          }"
          placeholder="Filter status"
          class="min-w-28"
        />
      </template>
    </UDashboardNavbar>
    <JobsList v-model="selectedJob" :jobs="filteredJobs" :statuses="statuses" />
  </UDashboardPanel>
  <JobsDetail v-if="selectedJob" :job="selectedJob" />
  <div v-else class="hidden lg:flex flex-1 items-center justify-center">
    <UIcon name="i-lucide-logs" class="size-32 text-dimmed" />
  </div>
</template>
<script setup lang="ts">
  import JobsList from '@/components/jobs/JobsList.vue'
  import JobsDetail from '@/components/jobs/JobsDetail.vue'
  import { useBackgroundJobs } from '@/stores/jobs'
  import { useTitle } from '@vueuse/core'
  import { computed, ref } from 'vue'
  const title = 'Задачи'
  useTitle(title)

  const { jobs } = useBackgroundJobs()

  const statusFilter = ref('all')
  const selectedJob = ref<BackgroundJob | null>()

  const filteredJobs = computed(() => {
    if (statusFilter.value === 'all') return jobs
    return jobs.filter((job) => job.status === statusFilter.value)
  })

  const statuses = [
    { label: 'все', value: 'all' },
    { label: 'ожид.', value: 'pending' },
    { label: 'идёт', value: 'running' },
    { label: 'готово', value: 'finished' },
    { label: 'ошибка', value: 'failed' },
  ]
</script>
