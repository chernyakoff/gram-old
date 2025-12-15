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

const labelsMap = {
  init: 'начат',
  engage: 'интерес',
  offer: 'диалог',
  closing: 'закрытие',
  complete: 'заявка',
  negative: 'негатив',
  operator: 'оператор',
  manual: 'ручной',
} as const

// --- series для area chart ---
const series = computed(() => {
  if (!props.statsData) return []

  const start = new Date(props.startDate)
  return Object.keys(props.statsData).map((key) => ({
    name: labelsMap[key as keyof typeof labelsMap],
    data: props.statsData[key as keyof StatsOut].map((value, idx) => {
      const d = new Date(start)
      d.setDate(start.getDate() + idx)
      return [d.getTime(), value] as [number, number]
    }),
  }))
})

const colors = [
  '#006a6c',
  '#8e90ff',
  '#ffab00',
  '#71dd37',
  '#ff5733',
  '#d32f2f',
  '#6a1b9a',
  '#455a64',
]

const options = computed<ApexOptions>(() => ({
  chart: {
    type: 'area',
    stacked: true,
    height: 350,
    toolbar: { show: false },
    zoom: { enabled: false },
  },
  colors,
  fill: {
    type: 'solid',
    opacity: 1, // области полностью непрозрачные
  },
  stroke: {
    width: 0, // убираем линии графика
  },
  tooltip: {
    theme: isDark.value ? 'dark' : 'light',
  },
  xaxis: {
    type: 'datetime',
    labels: {
      rotate: -90,
      datetimeFormatter: {
        day: 'dd.mm.yy', // формат даты, например 27 Oct
      },
      style: { colors: isDark.value ? 'rgba(170, 170, 170, 0.6)' : 'rgba(51, 51, 51, 0.6)' },
    },
  },
  yaxis: {
    labels: {
      style: { colors: isDark.value ? 'rgba(170, 170, 170, 0.6)' : 'rgba(51, 51, 51, 0.6)' },
    },
  },
  dataLabels: { enabled: false },

  legend: { show: false },
  grid: {
    borderColor: isDark.value ? 'rgba(119, 119, 119, 0.3)' : 'rgba(51, 51, 51, 0.3)',
    xaxis: { lines: { show: true } },
    yaxis: { lines: { show: true } },
  },
}))
</script>
