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
      <div class="min-w-[800px] max-w-4xl mx-auto">
        <UForm ref="form" :schema="projectInSchema" :state="state" @submit="onSubmit">
          <UTabs :items="tabs" variant="link" :ui="{ trigger: 'grow' }" class="gap-4 w-full">
            <template #info>
              <UFormField label="Наименование" name="name" class="mb-4">
                <UInput v-model="state.name" size="md" class="w-full" />
              </UFormField>
              <div class="mb-4 flex items-center gap-2">
                <UFormField label="Сообщений на одну переписку" name="dialogLimit">
                  <UInputNumber v-model="state.dialogLimit" size="md" />
                </UFormField>
                <UFormField label="Лимит исходящих сообщений" name="outDailyLimit">
                  <UInputNumber v-model="state.outDailyLimit" size="md" />
                </UFormField>
              </div>
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
            </template>
            <template #scenery>
              <UFormField name="prompt" class="w-full mb-4" label="Промпт для ИИ">
                <UTextarea :rows="14" v-model="state.prompt" placeholder="" class="w-full" />
              </UFormField>
            </template>
          </UTabs>
          <div class="flex items-center gap-10 justify-between w-full"></div>
        </UForm>
      </div>
    </template>
  </UDashboardPanel>
</template>
<script setup lang="ts">
import { onMounted, reactive } from 'vue'
import { useTitle } from '@vueuse/core'
import { useProjects } from '@/composables/use-projects'

import type { TabsItem } from '@nuxt/ui'
import { projectInSchema, type ProjectInSchema } from '@/schemas/projects'
import type { ProjectIn } from '@/types/openapi'
import type { FormSubmitEvent } from '@nuxt/ui'
import { parse } from 'valibot'
import { useTemplateRef } from 'vue'

const toast = useToast()
const form = useTemplateRef('form')

const tabs = [
  { label: 'Информация', icon: 'i-lucide-list', slot: 'info' as const },
  { label: 'Промпт', icon: 'i-lucide-image', slot: 'scenery' as const },
] satisfies TabsItem[]

const props = defineProps<{
  id?: number
}>()

//const isEdit = !!props.id
const hours = Array.from({ length: 24 }, (_, i) => ({
  label: i.toString().padStart(2, '0') + ':00',
  value: i,
}))

const { get, create, update } = useProjects()

const title = props.id ? `Редактировать проект` : 'Создать проект'

useTitle(title)

const getEmptyState = (): ProjectInSchema => ({
  name: '',
  dialogLimit: 1,
  outDailyLimit: 1,
  sendTimeStart: 0,
  sendTimeEnd: 23,
  firstMessage: '',
  prompt: '',
})

const actionTitle = props.id ? 'Сохранить' : 'Создать'
const toastTitle = props.id ? `Успешно сохранено` : 'Проект создан'

const state = reactive<ProjectInSchema>(getEmptyState())

const doSubmit = async () => {
  await form.value?.submit()
}

const onSubmit = async (event: FormSubmitEvent<ProjectInSchema>) => {
  const data = event.data satisfies ProjectIn
  toast.add({
    title: toastTitle,
    color: 'success',
  })
  if (!props.id) {
    await create(data)
  } else {
    await update(props.id, data)
  }
}

onMounted(async () => {
  if (props.id) {
    const dto = await get(props.id)
    Object.assign(state, parse(projectInSchema, dto))
  }
})
</script>
