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
          <div class="flex items-center gap-3">@{{ dialog.recipient }}</div>
          <span>{{ useDateFormat(dialog.startedAt, 'HH:MM DD.MM.YY') }}</span>
          <UChip :color="statusColor[dialog.status]" />
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
  init: 'neutral',
  engage: 'warning',
  offer: 'success',
  closing: 'info',
} as const

const dialogRefs = ref<Record<string, Element>>({})

const selectedDialog = defineModel<DialogOut | null>()

watch(selectedDialog, () => {
  if (!selectedDialog.value) {
    return
  }
  //Element implicitly has an 'any' type because index expression is not of type 'number'
  const ref = dialogRefs.value[selectedDialog.value.id]
  if (ref) {
    ref.scrollIntoView({ block: 'nearest' })
  }
})
</script>
