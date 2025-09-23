<template>
  <UDrawer direction="right" class="w-160" :handle="false" v-model:open="open">
    <template #body>
      <UTabs :items="tabs" variant="link" :ui="{ trigger: 'grow' }" class="gap-4 w-full">
        <template #profile>
          <div class="p-8">
            <ProfileTab v-model="state" :schema="accountSchema" />
          </div>
        </template>
        <template #photos>
          <div class="pt-2">
            <PhotosTab v-model="items" ref="photosTab" />
          </div>
        </template>
      </UTabs>
    </template>
    <template #footer>
      <UButton
        label="Сохранить"
        :disabled="isUnchanged"
        color="neutral"
        class="justify-center"
        @click="onSubmit"
      />
      <UButton
        label="Закрыть"
        color="neutral"
        variant="outline"
        class="justify-center"
        @click="$emit('update:open', false)"
      />
    </template>
  </UDrawer>
</template>
<script setup lang="ts">
import type { TabsItem } from '@nuxt/ui'
import { computed, reactive, ref, toRaw, watch } from 'vue'
import { accountSchema, getAccountData, type AccountSchema } from '@/schemas/account'

import { useAccounts } from '@/composables/useAccounts'
import { useUploadStore } from '@/stores/upload'
import { useBackgroundJobs } from '@/stores/jobs'

const open = defineModel<boolean>('open', { default: false })

const tabs = [
  {
    label: 'Профиль',
    icon: 'i-lucide-list',
    slot: 'profile' as const,
  },
  {
    label: 'Фото',
    icon: 'i-lucide-image',
    slot: 'photos' as const,
  },
] satisfies TabsItem[]

const toast = useToast()

const emit = defineEmits<{
  (e: 'completed'): void
  (e: 'update:open', value: boolean): void
}>()

const { account_id } = defineProps<{
  account_id: number
}>()

const { get, update } = useAccounts()
const { uploadAll, waitForAll } = useUploadStore()
const jobsStore = useBackgroundJobs()
const account = ref<Account>()
const state = reactive<AccountSchema>({} as AccountSchema)
const items = ref<EditableAccountPhoto[]>([])
const original = ref<AccountSchema | null>(null)

function isEqualObj(a: Record<string, unknown>, b: Record<string, unknown>) {
  const aKeys = Object.keys(a)
  const bKeys = Object.keys(b)
  if (aKeys.length !== bKeys.length) return false
  return aKeys.every((key) => a[key] === b[key])
}

const isUnchanged = computed(() => {
  if (!original.value) return true
  const basicUnchanged = isEqualObj(state, original.value)
  const photosChanged = items.value.some((p) => p.file || p.markedForDeletion)
  return basicUnchanged && !photosChanged
})

watch(
  [open, () => account_id],
  async ([isOpen, id]) => {
    if (isOpen && id) {
      const raw = await get(id)
      const photos: EditableAccountPhoto[] = raw.photos.map((p) => ({
        ...p,
        file: undefined,
        markedForDeletion: false,
      }))

      account.value = { ...raw, photos }
      Object.assign(state, await getAccountData(account.value))
      items.value = [...photos]
      original.value = {
        username: account.value.username,
        firstName: account.value.firstName,
        lastName: account.value.lastName,
        about: account.value.about,
        channel: account.value.channel,
      }
    }
  },
  { immediate: true },
)

watch(open, (val) => {
  if (!val) {
    Object.assign(state, {} as AccountSchema)
    items.value = []
    account.value = undefined
  }
})

async function onSubmit() {
  const photosRaw = items.value.map(toRaw)

  const { toDelete, toUpload } = photosRaw.reduce(
    (acc, p) => {
      if (p.file) acc.toUpload.push(p.file)
      else if (p.markedForDeletion) acc.toDelete.push(p.id)
      return acc
    },
    { toDelete: [] as number[], toUpload: [] as File[] },
  )

  open.value = false
  toast.add({
    title: 'Обновления данных аккаунта запущено',
    description: `Можно посмотреть ход выполнения в разделе «задачи»`,
    color: 'success',
  })

  uploadAll(toUpload, `media/${account_id}`)
  const results = await waitForAll()

  const payload = {
    ...toRaw(state),
    photos: {
      delete: toDelete,
      upload: results.fulfilled,
    },
  }

  console.log(results.rejected)
  console.log('state before submit:', toRaw(state))
  const { id } = await update(account_id, payload)
  jobsStore.add({
    id,
    name: 'Обновление аккаунта',
    onComplete: () => emit('completed'),
  })
}
</script>
