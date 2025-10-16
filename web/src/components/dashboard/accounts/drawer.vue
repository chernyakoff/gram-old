<template>
  <UDrawer direction="right" class="w-160" :handle="false" v-model:open="open" :draggable="false">
    <template #body>
      <UTabs :items="tabs" variant="link" :ui="{ trigger: 'grow' }" class="gap-4 w-full">
        <template #profile>
          <div class="p-8">
            <ProfileTab />
          </div>
        </template>
        <template #photos>
          <div class="pt-2">
            <GalleryTab />
          </div>
        </template>
      </UTabs>
    </template>
    <template #footer>
      <UButton
        label="Сохранить"
        :disabled="!editor.hasChanges"
        color="neutral"
        class="justify-center"
        @click="onSubmit"
      />
      <UButton
        label="Закрыть"
        color="neutral"
        variant="outline"
        class="justify-center"
        @click="open = false"
      />
    </template>
  </UDrawer>
</template>

<script setup lang="ts">
import type { TabsItem } from '@nuxt/ui'
import { watch } from 'vue'
import { useAccountEditor } from '@/stores/account-store'
import { useAccounts } from '@/composables/use-accounts'
import { useUploadStore } from '@/stores/upload-store'
import { useBackgroundJobs } from '@/stores/jobs-store'
import ProfileTab from './profile-tab.vue'
import GalleryTab from './gallery-tab.vue'

const tabs = [
  { label: 'Профиль', icon: 'i-lucide-list', slot: 'profile' as const },
  { label: 'Фото', icon: 'i-lucide-image', slot: 'photos' as const },
] satisfies TabsItem[]

const props = defineProps<{ accountId: number }>()
const open = defineModel<boolean>('open', { default: false })

const emit = defineEmits<{
  (e: 'completed'): void
}>()

const toast = useToast()
const editor = useAccountEditor()
const { get, update } = useAccounts()
const { uploadAll, waitForAll } = useUploadStore()
const jobsStore = useBackgroundJobs()

// Загрузка данных
watch(
  [open, () => props.accountId],
  async ([isOpen, id]) => {
    if (isOpen && id) {
      const account = await get(id)
      await editor.initialize(account)
    }
  },
  { immediate: true },
)

// Очистка
watch(open, (isOpen) => {
  if (!isOpen) editor.reset()
})

// Сохранение
async function onSubmit() {
  const { toUpload } = editor.photosChanges
  editor.isSaving = true
  open.value = false

  toast.add({
    title: 'Обновление данных аккаунта запущено',
    description: 'Можно посмотреть ход выполнения в разделе «задачи»',
    color: 'success',
  })

  uploadAll(toUpload, `media/${props.accountId}`)
  const results = await waitForAll()
  const payload = editor.createPayload(results.fulfilled)
  const { id } = await update(props.accountId, payload)

  jobsStore.add({
    id,
    name: 'Обновление аккаунта',
    onComplete: () => emit('completed'),
  })
  editor.isSaving = false
  editor.reset()
}
</script>
