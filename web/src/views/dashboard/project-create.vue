<template>
  <UDashboardPanel id="project-create">
    <template #header>
      <UDashboardNavbar :title="title" :ui="{ right: 'gap-3' }">
        <template #leading>
          <UDashboardSidebarCollapse />
        </template>
        <template #right>
          <UButton
            size="lg"
            label="Назад"
            variant="outline"
            color="neutral"
            @click="$router.back()"
          />
          <UButton size="lg" type="submit" :label="actionTitle" color="primary" @click="doSubmit" />
        </template>
      </UDashboardNavbar>
    </template>
    <template #body>
      <UForm ref="form" :schema="projectInSchema" :state="state" @submit="onSubmit">
        <div class="min-w-[800px] max-w-4xl mx-auto">
          <UFormField label="Наименование" name="name" class="mb-4">
            <UInput v-model="state.name" size="md" class="w-full" />
          </UFormField>

          <UFormField label="Сообщений на одну переписку" name="dialogLimit" class="mb-4">
            <UInputNumber v-model="state.dialogLimit" size="md" />
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
          <UFormField name="firstMessage" class="w-full mb-4" label="Текст первого сообщения">
            <UTextarea :rows="8" v-model="state.firstMessage" placeholder="" class="w-full" />
          </UFormField>
          <UTabs :items="tabs" variant="link" :ui="{ trigger: 'grow' }" class="gap-4 w-full">
            <template #generate>
              <UFormField name="brief.description" class="w-full mb-4" label="Описание">
                <UTextarea
                  :rows="8"
                  v-model="state.brief.description"
                  placeholder="Подробно опиши свой проект/услугу: что именно ты делаешь, для кого, какой основной продукт, какой результат даёшь клиентам?"
                  class="w-full"
                />
              </UFormField>
              <UFormField name="brief.offer" class="w-full mb-4" label="Цель">
                <UTextarea
                  :rows="8"
                  v-model="state.brief.offer"
                  placeholder="Какое бесплатное целевое действие ты хочешь предлагать в конце диалога? (примеры: бесплатный аудит, разбор воронки, стратегия на 3 месяца, консультация, чек-лист и т.д.)"
                  class="w-full"
                />
              </UFormField>
              <UFormField name="brief.client" class="w-full mb-4" label="Клиент">
                <UTextarea
                  :rows="8"
                  v-model="state.brief.client"
                  placeholder="Опиши портрет твоего идеального клиента максимально точно: возраст, пол, доход, профессия, где обитает, как говорит, какие страхи и желания."
                  class="w-full"
                />
              </UFormField>
              <UFormField name="brief.pains" class="w-full mb-4" label="Боли">
                <UTextarea
                  :rows="8"
                  v-model="state.brief.pains"
                  placeholder="Перечисли 3-5 самых острых и насущных болей твоей ЦА (то, от чего люди реально страдают и готовы платить за решение)."
                  class="w-full"
                />
              </UFormField>
              <UFormField name="brief.advantages" class="w-full mb-4" label="Преимущества">
                <UTextarea
                  :rows="8"
                  v-model="state.brief.advantages"
                  placeholder="Перечисли 3-5 твоих главных конкурентных преимуществ и уникальностей (чем ты лучше и отличаешься от всех остальных на рынке)."
                  class="w-full"
                />
              </UFormField>
              <UFormField name="brief.mission" class="w-full mb-4" label="Миссия">
                <UTextarea
                  :rows="8"
                  v-model="state.brief.mission"
                  placeholder="Ради чего ты вообще этим занимаешься? Какая у тебя миссия, почему это важно именно для тебя и для клиента?"
                  class="w-full"
                />
              </UFormField>
              <UFormField name="brief.focus" class="w-full mb-4" label="Фокус">
                <UTextarea
                  :rows="8"
                  v-model="state.brief.focus"
                  placeholder="На что ты больше всего обращал внимание, когда создавал свою услугу? (гарантии, формат, сопровождение, результат, методика и т.д.)"
                  class="w-full"
                />
              </UFormField>
              <UFormField class="w-full mb-4" label="Сгенерировать промпт">
                <UCheckbox />
              </UFormField>
            </template>
            <template #edit></template>
            <template #json></template>
          </UTabs>
        </div>

        <div class="flex items-center gap-10 justify-between w-full"></div>
      </UForm>
    </template>
  </UDashboardPanel>
</template>
<script setup lang="ts">
import { onMounted, reactive } from 'vue'
import { useTitle } from '@vueuse/core'
import { useProjects } from '@/composables/use-projects'

import { projectInSchema, type ProjectInSchema } from '@/schemas/projects'
import type { ProjectIn } from '@/types/openapi'
import type { FormSubmitEvent, TabsItem } from '@nuxt/ui'
import { parse } from 'valibot'
import { useTemplateRef } from 'vue'
import { useBackgroundJobs } from '@/stores/jobs-store'
import MTextrarea from '@/components/shared/m-textrarea.vue'

const jobsStore = useBackgroundJobs()

import { useRoute, useRouter } from 'vue-router'

const toast = useToast()
const form = useTemplateRef('form')

const tabs = [
  { label: 'Генерация', icon: 'bx:brain', slot: 'generate' as const },
  { label: 'Редактирование', icon: 'bx:edit', slot: 'edit' as const },
  { label: 'JSON', icon: 'bx:code-curly', slot: 'json' as const },
] satisfies TabsItem[]

const router = useRouter()

const route = useRoute()

const id = Number(route.params.id)

//const isEdit = !!props.id
const hours = Array.from({ length: 24 }, (_, i) => ({
  label: i.toString().padStart(2, '0') + ':00',
  value: i,
}))

const { get, create, update, default_project } = useProjects()

const title = id ? `Редактировать проект` : 'Создать проект'

useTitle(title)

const actionTitle = id ? 'Сохранить' : 'Создать'
const toastTitle = id ? `Успешно сохранено` : 'Проект создан'

const state = reactive<ProjectInSchema>({
  name: '',
  dialogLimit: 0,
  sendTimeStart: 0,
  sendTimeEnd: 24,
  firstMessage: '',
  brief: {
    description: '',
    offer: '',
    client: '',
    pains: '',
    advantages: '',
    mission: '',
    focus: '',
  },
  prompt: {},
})

const doSubmit = async () => {
  await form.value?.submit()
}

const onSubmit = async (event: FormSubmitEvent<ProjectInSchema>) => {
  const data = event.data satisfies ProjectIn
  let workflowId: string
  if (!id) {
    const res = await create(data)
    workflowId = res.id
  } else {
    const res = await update(id, data)
    workflowId = res.id
  }
  const toastData: Partial<Toast> = {
    title: toastTitle,
    color: 'success',
  }
  if (workflowId != 'NONE') {
    toastData.description =
      'Запущена генерация промпта (~2 мин.). Ход выполнения можно увидеть в разделе задачи'
    toast.add(toastData)
    jobsStore.add({
      id: workflowId,
      name: 'Обновление аккаунта',
    })
  } else {
    toast.add(toastData)
  }

  router.back()
}

onMounted(async () => {
  if (id) {
    const project = await get(id)
    Object.assign(state, parse(projectInSchema, project))
  } else {
    const def_project = await default_project()

    Object.assign(state, def_project)
  }
})
</script>
