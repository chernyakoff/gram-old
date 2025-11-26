<template>
  <div>
    <!-- Если есть badgeTitle, используем поповер -->
    <UPopover v-if="badgeTitle" mode="hover">
      <span
        class="inline-block px-3 py-1 rounded-full text-sm font-medium transition-colors"
        :class="badgeClasses"
      >
        {{ translations[account.status] }}
      </span>
      <template #content>
        {{ badgeTitle }}
      </template>
    </UPopover>

    <!-- Иначе просто обычный спан -->
    <span
      v-else
      class="inline-block px-3 py-1 rounded-full text-sm font-medium transition-colors"
      :class="badgeClasses"
      :title="badgeTitle"
    >
      {{ translations[account.status] }}
    </span>
  </div>
</template>

<script setup lang="ts">
import type { AccountOut, AccountStatus } from '@/types/openapi'
import { computed, defineProps } from 'vue'
import { useDateFormat } from '@vueuse/core'
interface Props {
  account: AccountOut
}

const { account } = defineProps<Props>()

const translations: Record<AccountStatus, string> = {
  good: 'Активен',
  banned: 'Забанен',
  muted: 'Ограничен',
  frozen: 'Заморожен',
  exited: 'Вышел',
}

const colors: Record<AccountStatus, string> = {
  good: 'bg-green-200 dark:bg-green-700 text-green-800 dark:text-green-200',
  banned: 'bg-red-200 dark:bg-red-700 text-red-800 dark:text-red-200',
  muted: 'bg-yellow-200 dark:bg-yellow-700 text-yellow-800 dark:text-yellow-200',
  frozen: 'bg-blue-200 dark:bg-blue-700 text-blue-800 dark:text-blue-200',
  exited: 'bg-gray-200 dark:bg-gray-700 text-gray-800 dark:text-gray-200',
}

const badgeClasses = computed(() => colors[account.status])

const badgeTitle = computed(() => {
  if (account.status === 'muted' && account.mutedUntil) {
    return `Ограничение до: ${useDateFormat(account.mutedUntil, 'DD.MM.YY').value}`
  }
  return undefined
})
</script>
