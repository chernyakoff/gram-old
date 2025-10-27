<template>
  <apexchart type="area" :options="options" :series="series" height="400" width="100%" />
</template>

<script setup lang="ts">
import type { StatsOut } from '@/types/openapi'
import type { ApexOptions } from 'apexcharts'
import { defineProps, computed, type PropType } from 'vue'

const props = defineProps({
  statsData: {
    type: Object as PropType<StatsOut>,
    required: true,
  },
  startDate: {
    type: String,
    required: true,
  },
})

const isDark = computed(() => document.documentElement.classList.contains('dark'))

// --- series для area chart ---
const series = computed(() => {
  if (!props.statsData) return []

  const start = new Date(props.startDate)
  return Object.keys(props.statsData).map((key) => ({
    name: key,
    data: props.statsData[key as keyof StatsOut].map((value, idx) => {
      const d = new Date(start)
      d.setDate(start.getDate() + idx)
      return [d.getTime(), value] as [number, number]
    }),
  }))
})

const options = computed<ApexOptions>(() => ({
  chart: {
    type: 'area',
    stacked: true,
    height: 350,
    toolbar: { show: false },
    zoom: { enabled: false },
  },
  xaxis: { type: 'datetime', labels: { rotate: -90 } },
  yaxis: { title: { text: 'Количество' } },
  dataLabels: { enabled: false },
  stroke: { curve: 'smooth' },
  legend: { position: 'top' },
  tooltip: { x: { format: 'dd MMM yyyy' } },
  grid: {
    borderColor: isDark.value ? 'rgba(119, 119, 119, 0.3)' : 'rgba(51, 51, 51, 0.3)',

    xaxis: { lines: { show: true } },
    yaxis: { lines: { show: true } },
  },
}))
</script>
