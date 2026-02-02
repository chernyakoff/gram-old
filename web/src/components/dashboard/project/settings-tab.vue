<template>
  <UForm ref="form" :schema="projectSettingsSchema" :state="state" @submit="onSubmit">
    <div class="min-w-[800px] max-w-4xl mx-auto">
      <UFormField label="Наименование" name="name" class="mb-4">
        <UInput v-model="state.name" size="md" class="w-full" />
      </UFormField>

      <UFormField label="Сообщений на одну переписку" name="dialogLimit" class="mb-4">
        <UInputNumber v-model="state.dialogLimit" size="md" />
      </UFormField>

      <UFormField label="Только премиум аккаунты" name="premiumRequired" class="mb-4">
        <USwitch v-model="state.premiumRequired" />
      </UFormField>

      <div class="mb-4 max-w-sm">
        <label class="block text-sm mb-2">Время рассылки</label>
        <div class="flex items-center gap-2">
          <UFormField name="sendTimeStart" class="w-auto">
            <USelect
              v-model="state.sendTimeStart"
              :items="hours"
              placeholder="С"
              class="w-auto min-w-[50px]"
            />
          </UFormField>

          <span class="px-2">до</span>

          <UFormField name="sendTimeEnd" class="w-auto">
            <USelect
              v-model="state.sendTimeEnd"
              :items="hours"
              placeholder="По"
              class="w-auto min-w-[50px]"
            />
          </UFormField>
        </div>
      </div>

      <div v-if="hasFirstMessage" class="w-full mb-4">
        <div class="flex items-center justify-between mb-1.5">
          <span class="text-sm font-medium">Текст первого сообщения</span>
          <div class="flex items-center gap-1 relative">
            <UModal v-if="state.firstMessage" title="Предпросмотр первого сообщения">
              <UButton icon="bx:show" color="neutral" variant="subtle"/>
              <template #body>
                {{ generateMessage(state.firstMessage) }}
              </template>
            </UModal>
           
          </div>
        </div>
        <UFormField name="firstMessage">
          <UTextarea :rows="8" v-model="state.firstMessage" placeholder="Заполните бриф и сгенерируйте промпт. Тут появится первое сообщение" class="w-full" />
        </UFormField>
      </div>

      <UButton type="submit">Сохранить</UButton>
    </div>
  </UForm>
  
</template>
<script setup lang="ts">
import { useProjects } from '@/composables/use-projects'
import {   onMounted, ref } from 'vue'
import { reactive } from 'vue'
import { generateMessage } from '@/utils/prompt'

import * as v from 'valibot'
import type { FormSubmitEvent } from '@nuxt/ui'

const { projectId } = defineProps<{
  projectId: number
}>()

const {  getSettings, saveSettings } = useProjects()

const toast = useToast()

const hasFirstMessage = ref(false)

const limitShema = v.pipe(
  v.number(),
  v.minValue(1, 'должно быть больше 1'),
  v.maxValue(100, 'должно быть не больше 100'),
)

const textSchema = v.pipe(
  v.string('должно быть строкой'),
  v.nonEmpty('обязательное поле'),
  v.minLength(32, 'должно содержать хотя бы 32 символа'),
)

const hourSchema = v.pipe(v.number('обязательное поле'), v.minValue(0), v.maxValue(24))

const projectSettingsSchema = v.object({
  name: v.pipe(
    v.string(),
    v.nonEmpty('обязательное поле'),
    v.maxLength(64, 'должно содержать не более 64 символов'),
  ),
  dialogLimit: limitShema,
  sendTimeStart: hourSchema,
  sendTimeEnd: hourSchema,
  firstMessage: v.nullish(textSchema),
  premiumRequired: v.boolean(),
})
type ProjectSettingsSchema = v.InferOutput<typeof projectSettingsSchema>

const hours = Array.from({ length: 24 }, (_, i) => ({
  label: i.toString().padStart(2, '0') + ':00',
  value: i,
}))


const state = reactive<ProjectSettingsSchema>({
  name: '',
  dialogLimit: 0,
  sendTimeStart: 10,
  sendTimeEnd: 21,
  firstMessage: '',
  premiumRequired: true,
})


onMounted(async () => {
  const response = await getSettings(projectId)
  Object.assign(state, response)
    hasFirstMessage.value =
    typeof response.firstMessage === 'string' &&
    response.firstMessage.trim().length > 0

  if (!hasFirstMessage.value) {
    state.firstMessage = undefined
  }
})

const onSubmit = async (event: FormSubmitEvent<ProjectSettingsSchema>) => {
  await saveSettings(projectId, event.data)
  toast.add({
    title: 'Настройки проекта успешно сохранены',
    color: 'success',
  })
}
</script>
