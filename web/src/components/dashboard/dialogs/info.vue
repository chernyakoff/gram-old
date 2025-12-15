<template>
  <div
    class="flex flex-wrap items-center justify-between gap-6 px-4 py-2 shadow bg-white dark:bg-gray-800 w-full"
  >
    <!-- Статус -->
    <div class="flex items-center gap-2">
      <div
        class="w-3 h-3 rounded-full"
        :style="{ backgroundColor: statusColor[props.dialog.status] }"
      ></div>
      <span class="font-semibold capitalize">{{ labelsMap[props.dialog.status] }}</span>
    </div>

    <!-- Получатель -->
    <div class="flex flex-col">
      <span class="text-gray-500 text-xs">Получатель</span>
      <span class="font-medium">@{{ props.dialog.recipient }}</span>
    </div>

    <!-- Аккаунт -->
    <div class="flex flex-col">
      <span class="text-gray-500 text-xs">Аккаунт</span>
      <span class="font-medium">@{{ props.dialog.account }}</span>
    </div>

    <!-- Проект -->
    <div class="flex flex-col">
      <span class="text-gray-500 text-xs">Проект</span>
      <span class="font-medium">{{ props.dialog.project }}</span>
    </div>

    <!-- Дата -->
    <div class="flex flex-col">
      <span class="text-gray-500 text-xs">Начат</span>
      <span class="font-medium">
        {{
          new Date(props.dialog.startedAt).toLocaleString('ru-RU', {
            dateStyle: 'short',
            timeStyle: 'short',
          })
        }}
      </span>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { DialogOut } from '@/types/openapi'
import { labelsMap, statusColor } from '@/utils/status'

const props = defineProps({
  dialog: {
    type: Object as () => DialogOut,
    required: true,
  },
})
</script>
