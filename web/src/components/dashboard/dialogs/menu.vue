<template>
  <div class="overflow-y-auto divide-y divide-default">
    <div
      v-for="(dialog, index) in dialogs"
      :key="index"
      :ref="
        (el) => {
          dialogRefs[dialog.id] = el as Element
        }
      "
    >
      <div
        class="p-4 sm:px-6 text-sm cursor-pointer border-l-2 transition-colors"
        :class="[
          selectedDialog && selectedDialog.id === dialog.id
            ? 'border-primary bg-primary/10'
            : 'border-(--ui-bg) hover:border-primary hover:bg-primary/5',
        ]"
        @click="selectedDialog = dialog"
      >
        <div class="flex items-center justify-between">
          <div class="flex flex-col gap-1">
            <div class="flex items-center gap-3">@{{ dialog.recipient }}</div>
            <span class="text-xs text-muted">
              {{ useDateFormat(dialog.startedAt, 'HH:mm DD.MM.YY') }}
            </span>
          </div>
          <!-- Простой кружочек -->
          <span
            class="w-3 h-3 rounded-full"
            :style="{ backgroundColor: statusColor[dialog.status] }"
          />
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { watch } from 'vue'
import { ref } from 'vue'

import { useDateFormat } from '@vueuse/core'
import type { DialogOut } from '@/types/openapi'

defineProps<{
  dialogs: DialogOut[]
}>()

const statusColor = {
  init: '#006a6c', // темно-бирюзовый — начальный статус, нейтральный
  engage: '#8e90ff', // светло-синий — общение с юзером активно
  offer: '#ffab00', // оранжевый — предложение/коммерческий интерес
  closing: '#71dd37', // зеленый — этап заключения сделки
  complete: '#ff5733', // красно-оранжевый — завершено, финальный статус
  negative: '#d32f2f', // ярко-красный — юзер недоволен общением
  operator: '#6a1b9a', // фиолетовый — юзер хочет живого человека, вмешательство оператора
} as const

const dialogRefs = ref<Record<string, Element>>({})

const selectedDialog = defineModel<DialogOut | null>()

watch(selectedDialog, () => {
  if (!selectedDialog.value) {
    return
  }
  const ref = dialogRefs.value[selectedDialog.value.id]
  if (ref) {
    ref.scrollIntoView({ block: 'nearest' })
  }
})
</script>
