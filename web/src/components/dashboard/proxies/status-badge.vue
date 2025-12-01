<template>
  <span
    class="inline-block px-3 py-1 rounded-full text-sm font-medium transition-colors"
    :class="badgeClasses"
  >
    {{ badgeText }}
  </span>
</template>
<script setup lang="ts">
import { computed, defineProps } from 'vue'
import type { ProxyOut } from '@/types/openapi'

interface Props {
  proxy: ProxyOut
}

const { proxy } = defineProps<Props>()

type ProxyStatus = 'working' | 'unstable' | 'disabled'

const proxyStatus = computed<ProxyStatus>(() => {
  if (!proxy.active) return 'disabled'
  if (proxy.failures > 0) return 'unstable'
  return 'working'
})

const statusText: Record<ProxyStatus, string> = {
  working: 'Работает',
  unstable: 'Нестабильный',
  disabled: 'Отключён',
}

const colors: Record<ProxyStatus, string> = {
  working: 'bg-green-200 dark:bg-green-700 text-green-900 dark:text-green-200',
  unstable: 'bg-yellow-200 dark:bg-yellow-700 text-yellow-900 dark:text-yellow-200',
  disabled: 'bg-red-200 dark:bg-red-700 text-red-900 dark:text-red-200',
}

const badgeClasses = computed(() => colors[proxyStatus.value])

const badgeText = computed(() => {
  if (proxyStatus.value === 'unstable') {
    return `${statusText.unstable} (${proxy.failures})`
  }
  return statusText[proxyStatus.value]
})
</script>
