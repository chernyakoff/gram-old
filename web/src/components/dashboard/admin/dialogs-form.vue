<template>
  <UForm ref="form" :schema="thisSchema" :state="state" @submit="onSubmit">
    <UFormField label="Username" name="username" class="mb-4">
      <UInput
        v-model="state.username"
        size="md"
        class="w-full"
        :disabled="loading"
        icon="i-lucide-at-sign"
      />
    </UFormField>

    <UFormField label="Статус" name="days" class="mb-4">
      <USelect
        v-model="state.status"
        :items="statuses"
        :ui="{
          trailingIcon: 'group-data-[state=open]:rotate-180 transition-transform duration-200',
        }"
        placeholder="Filter status"
        class="min-w-28"
      />
    </UFormField>

    <UButton type="submit" :loading="loading" :disabled="loading">Скачать диалоги</UButton>
  </UForm>
</template>

<script setup lang="ts">
import type { DialogsDownloadIn } from '@/types/openapi'
import type { FormSubmitEvent } from '@nuxt/ui'
import { useTitle } from '@vueuse/core'
import { reactive } from 'vue'
import { useAdmin } from '@/composables/use-admin'
import * as v from 'valibot'
import * as telegram from '@/schemas/atoms/telegram'
import { statuses } from '@/utils/status'

const title = 'Админка - Выгрузка'

useTitle(title)

const thisSchema = v.object({
  username: telegram.username(),
  status: v.optional(
    v.picklist([
      'all',
      'init',
      'engage',
      'offer',
      'closing',
      'complete',
      'negative',
      'operator',
      'manual',
    ]),
  ),
})

type ThisSchema = v.InferOutput<typeof thisSchema>

const { downloadDialogs, loading } = useAdmin()

const state = reactive({
  username: '',
  status: 'all',
})

const onSubmit = async (event: FormSubmitEvent<ThisSchema>) => {
  const payload: DialogsDownloadIn = {
    username: event.data.username,
    status: event.data.status === 'all' ? undefined : event.data.status,
  }

  await downloadDialogs(payload)
}
</script>
