<template>
  <UForm ref="form" :schema="appSettingSchema" :state="state" @submit="onSubmit">
    <div class="min-w-[800px] max-w-4xl mx-auto">
      <UFormField :label="label" name="value" class="mb-4">
        <MTextrarea :fullscreenTitle="label" :rows="8" v-model="state.value" class="w-full" />
      </UFormField>

      <UInput v-model="state.path" type="hidden" name="path" />

      <UButton type="submit" :loading="loading" :disabled="loading">Сохранить</UButton>
    </div>
  </UForm>
</template>

<script setup lang="ts">
import { appSettingSchema, type AppSettingSchema } from '@/schemas/admin'
import type { FormSubmitEvent } from '@nuxt/ui'
import { useTitle } from '@vueuse/core'
import { reactive, onMounted } from 'vue'
import { useAdmin } from '@/composables/use-admin'
import MTextrarea from '@/components/shared/m-textrarea.vue'
const toast = useToast()

const { label, path } = defineProps<{
  label: string
  path: string
}>()

useTitle(`Админка - ${label}`)

const { getAppSetting, saveAppSetting, loading, error, success } = useAdmin()

const state = reactive({
  value: '',
  path,
})

onMounted(async () => {
  try {
    const value = await getAppSetting(path)
    if (typeof value === 'string') {
      state.value = value
    }
  } catch (e) {
    console.log(e)
    toast.add({
      title: 'Ошибка загрузки',
      description: 'Не получилось получить текущее значение настройки.',
      color: 'error',
    })
  }
})

const onSubmit = async (event: FormSubmitEvent<AppSettingSchema>) => {
  const data = event.data satisfies AppSettingSchema

  await saveAppSetting(data)

  if (error.value) {
    toast.add({
      title: 'Ошибка',
      description: error.value,
      color: 'error',
    })
    return
  }

  if (success.value) {
    toast.add({
      title: 'Сохранено',
      description: 'Настройка успешно обновлена',
      color: 'success',
    })
  }
}
</script>
