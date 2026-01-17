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

      <div class="w-full mb-4">
        <div class="flex items-center justify-between mb-1.5">
          <span class="text-sm font-medium">Текст первого сообщения</span>
          <div class="flex items-center gap-1 relative">
            <UModal title="Предпросмотр первого сообщения">
              <UButton icon="bx:show" color="neutral" variant="subtle" v-if="disableSynonimize" />
              <template #body>
                {{ generateMessage(state.firstMessage) }}
              </template>
            </UModal>
            <UButton
              icon="bx:cube-alt"
              color="neutral"
              variant="subtle"
              @click="doSynonimize"
              v-if="!disableSynonimize"
            />
          </div>
        </div>
        <UFormField name="firstMessage">
          <UTextarea :rows="8" v-model="state.firstMessage" placeholder="" class="w-full" />
        </UFormField>
      </div>

      <UButton type="submit">Сохранить</UButton>
    </div>
  </UForm>
  <BlockingModal
    title="Рандомизирую"
    text="Дождитесь окончания рандомизации"
    :open="isRandomizing"
  />
</template>
<script setup lang="ts">
import { useProjects } from '@/composables/use-projects'
import { computed, onMounted } from 'vue'
import { reactive, ref } from 'vue'
import { generateMessage } from '@/utils/prompt'
import BlockingModal from '@/components/shared/blocking-modal.vue'

import * as v from 'valibot'
import type { FormSubmitEvent } from '@nuxt/ui'

const { projectId } = defineProps<{
  projectId: number
}>()

const { synonimize, getSettings, saveSettings } = useProjects()

const toast = useToast()

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
  firstMessage: textSchema,
  premiumRequired: v.boolean(),
})
type ProjectSettingsSchema = v.InferOutput<typeof projectSettingsSchema>

const hours = Array.from({ length: 24 }, (_, i) => ({
  label: i.toString().padStart(2, '0') + ':00',
  value: i,
}))

const disableSynonimize = computed(() => {
  // Ищем текст вида {что-то|что-то}
  const regex = /\{[^{}|]+\|[^{}]+\}/
  return regex.test(state.firstMessage)
})

const state = reactive<ProjectSettingsSchema>({
  name: '',
  dialogLimit: 0,
  sendTimeStart: 10,
  sendTimeEnd: 21,
  firstMessage: '',
  premiumRequired: true,
})

const isRandomizing = ref(false)

const doSynonimize = async () => {
  if (state.firstMessage.length < 1) {
    return
  }
  isRandomizing.value = true
  const { text } = await synonimize({ text: state.firstMessage })
  state.firstMessage = text
  isRandomizing.value = false
}

onMounted(async () => {
  const response = await getSettings(projectId)
  Object.assign(state, response)
})

const onSubmit = async (event: FormSubmitEvent<ProjectSettingsSchema>) => {
  await saveSettings(projectId, event.data)
  toast.add({
    title: 'Настройки проекта успешно сохранены',

    color: 'success',
  })
}
</script>
