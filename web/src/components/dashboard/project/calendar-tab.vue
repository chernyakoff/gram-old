<template>
  <UForm ref="form" :schema="calendarSchema" :state="state" @submit="onSubmit">
    <div class="min-w-[800px] max-w-4xl mx-auto mt-8">
      <UFormField name="useCalendar" class="w-full mb-4" label="Использовать календарь?">
        <USwitch
          :rows="6"
          v-model="state.useCalendar"
          description="Назначать встречи согласно расписанию, заданному в Календаре"
          class="w-full"
        />
      </UFormField>
      <UFormField name="morningReminder" class="w-full mb-4" label="Утреннее напоминание">
        <UTextarea
          :rows="6"
          v-model="state.morningReminder"
          placeholder="Сообщение, которое будет отправляться утром в день встречи. «Утро» это начало рассылки в настройках проекта. Можно ничего не указывать если вам это не нужно.&#10;&#10;Например: Добрый день, у нас сегодня встреча в {TIME}, ничего не изменилось все в силе?&#10;&#10;Допустимые теги: {TIME} {DATE} {DATETIME}"
          class="w-full"
        />
      </UFormField>
      <UFormField name="client" class="w-full mb-4" label="Напоминание перед встречей">
        <UTextarea
          :rows="6"
          v-model="state.meetingReminder"
          placeholder="Сообщение которое будет отправляться за час до встречи. Можно ничего не укзаывать если вам это не нужно.&#10;&#10;Например: Напоминаю, что у нас встреча в {TIME}, спасибо"
          class="w-full"
        />
      </UFormField>

      <UButton type="submit" name="action" value="save">Сохранить</UButton>
    </div>
  </UForm>
</template>
<script lang="ts" setup>
import { useProjects } from '@/composables/use-projects'
import { onMounted } from 'vue'
import { reactive } from 'vue'

import * as v from 'valibot'
import type { FormSubmitEvent } from '@nuxt/ui'

const { getCalendar, saveCalendar } = useProjects()

const { projectId } = defineProps<{
  projectId: number
}>()

const toast = useToast()

const textSchema = v.pipe(
  v.string('должно быть строкой'),
  v.minLength(32, 'должно содержать хотя бы 32 символа'),
)

const calendarSchema = v.object({
  useCalendar: v.boolean(),
  morningReminder: v.nullish(textSchema),
  meetingReminder: v.nullish(textSchema),
})

type CalendarSchema = v.InferOutput<typeof calendarSchema>

const state = reactive<CalendarSchema>({
  useCalendar: false,
  morningReminder: '',
  meetingReminder: '',
})

onMounted(async () => {
  const response = await getCalendar(projectId)
  Object.assign(state, response)
})

const onSubmit = async (event: FormSubmitEvent<CalendarSchema>) => {
  await saveCalendar(projectId, event.data)
  toast.add({
    title: 'Настройки календаря сохранёны',
    color: 'success',
  })
}
</script>
