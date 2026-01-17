<template>
  <UForm ref="form" :schema="projectBriefSchema" :state="state" @submit="onSubmit">
    <div class="min-w-[800px] max-w-4xl mx-auto">
      <UFormField name="description" class="w-full mb-4" label="Описание">
        <UTextarea
          :rows="6"
          v-model="state.description"
          placeholder="Подробно опиши свой проект/услугу: что именно ты делаешь, для кого, какой основной продукт, какой результат даёшь клиентам?"
          class="w-full"
        />
      </UFormField>
      <UFormField name="offer" class="w-full mb-4" label="Цель">
        <UTextarea
          :rows="6"
          v-model="state.offer"
          placeholder="Какое бесплатное целевое действие ты хочешь предлагать в конце диалога? (примеры: бесплатный аудит, разбор воронки, стратегия на 3 месяца, консультация, чек-лист и т.д.)"
          class="w-full"
        />
      </UFormField>
      <UFormField name="client" class="w-full mb-4" label="Клиент">
        <UTextarea
          :rows="6"
          v-model="state.client"
          placeholder="Опиши портрет твоего идеального клиента максимально точно: возраст, пол, доход, профессия, где обитает, как говорит, какие страхи и желания."
          class="w-full"
        />
      </UFormField>
      <UFormField name="pains" class="w-full mb-4" label="Боли">
        <UTextarea
          :rows="6"
          v-model="state.pains"
          placeholder="Перечисли 3-5 самых острых и насущных болей твоей ЦА (то, от чего люди реально страдают и готовы платить за решение)."
          class="w-full"
        />
      </UFormField>
      <UFormField name="advantages" class="w-full mb-4" label="Преимущества">
        <UTextarea
          :rows="6"
          v-model="state.advantages"
          placeholder="Перечисли 3-5 твоих главных конкурентных преимуществ и уникальностей (чем ты лучше и отличаешься от всех остальных на рынке)."
          class="w-full"
        />
      </UFormField>
      <UFormField name="mission" class="w-full mb-4" label="Миссия">
        <UTextarea
          :rows="6"
          v-model="state.mission"
          placeholder="Ради чего ты вообще этим занимаешься? Какая у тебя миссия, почему это важно именно для тебя и для клиента?"
          class="w-full"
        />
      </UFormField>
      <UFormField name="focus" class="w-full mb-4" label="Фокус">
        <UTextarea
          :rows="6"
          v-model="state.focus"
          placeholder="На что ты больше всего обращал внимание, когда создавал свою услугу? (гарантии, формат, сопровождение, результат, методика и т.д.)"
          class="w-full"
        />
      </UFormField>
      <div class="flex gap-2">
        <UButton type="submit" name="action" variant="outline" value="save">Сохранить</UButton>

        <UButton type="submit" name="action" value="generate" color="primary">
          Сгенерировать промпт
        </UButton>
      </div>
    </div>
  </UForm>
  <BlockingModal
    title="Генерация промпта"
    text="Генерация промпта для вашего проекта займёт 1-2 минуты. Пожалуйста, не закрывайте страницу и дождитесь завершения процесса."
    :open="isGenerating"
  />
</template>
<script lang="ts" setup>
import { useProjects } from '@/composables/use-projects'
import { onMounted } from 'vue'
import { reactive, ref } from 'vue'
import BlockingModal from '@/components/shared/blocking-modal.vue'
const jobsStore = useBackgroundJobs()

import * as v from 'valibot'
import type { FormSubmitEvent } from '@nuxt/ui'
import { useBackgroundJobs } from '@/stores/jobs-store'

const { getBrief, saveBrief, generatePrompt } = useProjects()

const { projectId } = defineProps<{
  projectId: number
}>()

const isGenerating = ref(false)

const toast = useToast()

const textSchema = v.pipe(
  v.string('должно быть строкой'),
  v.nonEmpty('обязательное поле'),
  v.minLength(32, 'должно содержать хотя бы 32 символа'),
)

const projectBriefSchema = v.object({
  description: textSchema,
  client: textSchema,
  offer: textSchema,
  pains: textSchema,
  advantages: textSchema,
  mission: textSchema,
  focus: textSchema,
})

type ProjectBriefSchema = v.InferOutput<typeof projectBriefSchema>

const state = reactive<ProjectBriefSchema>({
  description: '',
  client: '',
  offer: '',
  pains: '',
  advantages: '',
  mission: '',
  focus: '',
})

onMounted(async () => {
  const response = await getBrief(projectId)
  Object.assign(state, response)
})

const onSubmit = async (event: FormSubmitEvent<ProjectBriefSchema>) => {
  const action = event.submitter?.getAttribute('value')
  if (action === 'save') {
    await saveBrief(projectId, event.data)
    toast.add({
      title: 'Бриф успешно сохранён',
      color: 'success',
    })
    return
  }
  if (action === 'generate') {
    isGenerating.value = true
    const res = await generatePrompt(projectId, event.data)
    isGenerating.value = true

    jobsStore.add({
      id: res.id,
      name: 'Генерация промпта',
      onComplete: () => {
        // Закрываем модальное окно
        isGenerating.value = false

        // Показываем успешное уведомление
        toast.add({
          title: 'Промпт успешно сгенерирован',
          description: 'Генерация промпта завершена',
          color: 'success',
        })
      },
    })
    toast.add({
      title: 'Промпт сгенерирован',
      color: 'success',
    })
  }
}
</script>
