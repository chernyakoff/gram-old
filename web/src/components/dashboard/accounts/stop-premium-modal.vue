<template>
  <UModal v-model:open="open" :title="`Отмена подписки`" :description="`Для ${accountName}`">
    <button class="flex items-center gap-1">
      <UIcon name="bxs:star" class="h-6 w-6 text-yellow-400" />
    </button>
    <template #footer="{ close }">
      <div class="flex justify-end gap-2">
        <UButton label="Закрыть" color="neutral" variant="subtle" @click="close" />
        <UButton
          label="Отменить подписку"
          color="primary"
          variant="solid"
          loading-auto
          @click="onSubmit"
        />
      </div>
    </template>
  </UModal>
</template>

<script setup lang="ts">
import { computed } from 'vue'

import { useAccounts } from '@/composables/use-accounts'
import type { AccountOut } from '@/types/openapi'
import { useBackgroundJobs } from '@/stores/jobs-store'

const jobsStore = useBackgroundJobs()
const toast = useToast()

const { account } = defineProps<{ account: AccountOut }>()
const open = defineModel<boolean>('open', { default: false })

const accountName = computed(() => `${account.firstName ?? ''} ${account.lastName ?? ''}`)

const emit = defineEmits<{
  (e: 'completed'): void
}>()

const { stopPremium } = useAccounts()

const onSubmit = async () => {
  open.value = false
  toast.add({
    title: 'Отмена подписки запущена',
    description: `Можно посмотреть ход выполнения в разделе «задачи»`,
    color: 'success',
  })

  const { id } = await stopPremium(account.id)
  jobsStore.add({
    id,
    name: `Отмена подписки ${account.phone}`,
    onComplete: () => emit('completed'),
  })
}
</script>
