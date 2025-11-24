<template>
  <div class="grid grid-cols-2 gap-y-2 gap-x-6 mt-4">
    <div v-for="(cat, i) in categories" :key="i" class="flex items-center justify-between text-sm">
      <div class="flex items-center gap-2">
        <span class="w-3 h-3 rounded-full" :style="{ backgroundColor: colors[i] }"></span>
        <span>{{ cat }}</span>
      </div>
      <span class="font-bold">{{ summedData[i] }}</span>
    </div>
  </div>
  <apexchart type="bar" :options="options" :series="series" height="300" width="100%" />
</template>

<script setup lang="ts">
import type { StatsOut } from '@/types/openapi'
import type { ApexOptions } from 'apexcharts'
import { defineProps, computed, type PropType } from 'vue'

const { statsData } = defineProps({
  statsData: {
    type: Object as PropType<StatsOut>,
    required: true,
  },
})

const categories = ['начат', 'интерес', 'заявка', 'закрытие', 'закрыт']

const colors = ['#006a6c', '#8e90ff', '#ffab00', '#71dd37', '#ff5733']

const shortLabels = ['5', '4', '3', '2', '1']

// Суммируем каждую категорию
const summedData = computed(() => {
  if (!statsData) return [0, 0, 0, 0]
  return [
    statsData.init.reduce((sum, val) => sum + val, 0),
    statsData.engage.reduce((sum, val) => sum + val, 0),
    statsData.offer.reduce((sum, val) => sum + val, 0),
    statsData.closing.reduce((sum, val) => sum + val, 0),
    statsData.complete.reduce((sum, val) => sum + val, 0),
  ]
})

// Максимум для нормализации
const maxVal = computed(() => Math.max(...summedData.value, 1))

// Используем короткие метки для оси Y, но полные для тултипа
const series = computed(() => [
  {
    name: 'CTR',
    data: summedData.value.map((val, idx) => ({
      x: shortLabels[idx], // Короткая метка для оси Y
      y: ((val / maxVal.value) * 100).toFixed(1),
      fullName: categories[idx], // Сохраняем полное название для тултипа
    })),
  },
])

const isDark = computed(() => document.documentElement.classList.contains('dark'))

type customTooltipParams = {
  seriesIndex: number
  dataPointIndex: number
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  w: any
}

const options = computed<ApexOptions>(() => ({
  chart: {
    type: 'bar',
    stacked: false,
    toolbar: { show: false },
    zoom: { enabled: false },
  },
  colors,
  fill: { opacity: 1 },
  tooltip: {
    theme: isDark.value ? 'dark' : 'light',
    custom: ({ seriesIndex, dataPointIndex, w }: customTooltipParams) => {
      const data = w.config.series[seriesIndex].data[dataPointIndex]
      const value = data.y
      const fullName = data.fullName
      const color = colors[dataPointIndex]
      const headerBg = isDark.value ? '#1a1a1a' : '#f5f5f5'
      const bodyBg = isDark.value ? '#2d2d2d' : '#ffffff'
      const textColor = isDark.value ? '#e0e0e0' : '#333333'
      return `<div class="apexcharts-tooltip-box" style="padding: 0; min-width: 150px; background-color: ${bodyBg}; border-radius: 6px; overflow: hidden; box-shadow: 0 2px 8px rgba(0,0,0,0.15);">
        <div style="margin:0;padding: 8px 12px; background-color: ${headerBg}; font-weight: 500; font-size: 12px; color: ${textColor};">${fullName}</div>
        <div style="padding: 10px 12px; display: flex; align-items: center; gap: 8px;">
          <span style="width: 10px; height: 10px; border-radius: 50%; background-color: ${color}; display: inline-block;"></span>
          <span style="font-weight: 600; color: ${textColor}; font-size: 13px;">CTR: ${value}%</span>
        </div>
      </div>`
    },
  },
  plotOptions: {
    bar: {
      horizontal: true,
      borderRadius: 10,
      borderRadiusApplication: 'end',
      //endingShape: "rounded",
      distributed: true,
    },
  },
  xaxis: {
    min: 0,
    max: 100,
    tickAmount: 5,
    labels: {
      formatter: (val: unknown): string => `${val}%`,
      style: { colors: isDark.value ? 'rgba(170, 170, 170, 0.6)' : 'rgba(51, 51, 51, 0.6)' },
    },
    axisBorder: { show: false },
    axisTicks: { show: false },
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
    strokeDashArray: 12,
    xaxis: { lines: { show: true } },
    yaxis: { lines: { show: false } },
  },
}))
</script>
