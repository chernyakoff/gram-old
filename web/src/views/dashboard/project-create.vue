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
          <UButton
            size="lg"
            type="submit"
            :disabled="isButtonDisabled"
            :label="actionTitle"
            color="primary"
            @click="doSubmit"
          />
        </template>
      </UDashboardNavbar>
    </template>
    <template #body>
      <UForm ref="form" :schema="projectInSchema" :state="state" @submit="onSubmit">
        <UStepper :items="items" class="w-full" :linear="linear" v-model="currentStep">
          <template #settings>
            <div class="min-w-[800px] max-w-4xl mx-auto">
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
            </div>
          </template>
          <template #prompt>
            <div class="min-w-[800px] max-w-4xl mx-auto">
              <UFormField name="prompt" class="w-full mb-4" label="Роль">
                <TiptapField v-model="state.role" min-height="200px" />
              </UFormField>
              <UFormField name="prompt" class="w-full mb-4" label="Контекст">
                <TiptapField v-model="state.context" min-height="200px" />
              </UFormField>
              <UFormField name="prompt" class="w-full mb-4" label="Инструкции">
                <TiptapField v-model="state.instruction" min-height="300px" />
              </UFormField>
              <UFormField name="prompt" class="w-full mb-4" label="Правила">
                <TiptapField v-model="state.rules" min-height="200px" />
              </UFormField>
            </div>
          </template>
          <template #init>
            <div class="min-w-[800px] max-w-4xl mx-auto">
              <UFormField name="prompt" class="w-full mb-4" label="INIT">
                <TiptapField v-model="state.init" min-height="calc(100vh - 17rem)" />
              </UFormField>
            </div>
          </template>
          <template #engage>
            <div class="min-w-[800px] max-w-4xl mx-auto">
              <UFormField name="prompt" class="w-full mb-4" label="ENGAGE">
                <TiptapField v-model="state.engage" min-height="calc(100vh - 17rem)" />
              </UFormField>
            </div>
          </template>
          <template #offer>
            <div class="min-w-[800px] max-w-4xl mx-auto">
              <UFormField name="prompt" class="w-full mb-4" label="OFFER">
                <TiptapField v-model="state.offer" min-height="calc(100vh - 17rem)" />
              </UFormField>
            </div>
          </template>
          <template #closing>
            <div class="min-w-[800px] max-w-4xl mx-auto">
              <UFormField name="prompt" class="w-full mb-4" label="CLOSING">
                <TiptapField v-model="state.closing" min-height="calc(100vh - 17rem)" />
              </UFormField>
            </div>
          </template>
        </UStepper>

        <div class="flex items-center gap-10 justify-between w-full"></div>
      </UForm>
    </template>
  </UDashboardPanel>
</template>
<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { useTitle } from '@vueuse/core'
import { useProjects } from '@/composables/use-projects'

import { projectInSchema, type ProjectInSchema } from '@/schemas/projects'
import type { ProjectIn } from '@/types/openapi'
import type { FormSubmitEvent } from '@nuxt/ui'
import { parse } from 'valibot'
import { useTemplateRef } from 'vue'
import TiptapField from '@/components/shared/tiptap-field.vue'
import type { StepperItem } from '@nuxt/ui'
import { useRouter } from 'vue-router'

const items = [
  {
    slot: 'settings' as const,
    title: 'настройки',

    icon: 'bx:cog',
  },
  {
    slot: 'prompt' as const,
    title: 'промпт',
    icon: 'bx:message-square-detail',
  },
  {
    slot: 'init' as const,
    title: 'init',
    description: 'знакомство',
    icon: 'bx:user-check',
  },
  {
    slot: 'engage' as const,
    description: 'привлечение',
    title: 'engage',
    icon: 'bx:bxs-cat',
  },
  {
    slot: 'offer' as const,
    description: 'предложение',
    title: 'offer',
    icon: 'bx:bxs-phone-outgoing',
  },
  {
    slot: 'closing' as const,
    description: 'завершение',
    title: 'closing',
    icon: 'bx:bxs-happy-beaming',
  },
] satisfies StepperItem[]

const toast = useToast()
const form = useTemplateRef('form')

const router = useRouter()

const props = defineProps<{
  id?: number
}>()

const linear = computed(() => !props?.id)

const currentStep = ref(0)

const isButtonDisabled = computed(() => {
  if (props.id) return false // update
  return currentStep.value !== items.length - 1 // create
})

//const isEdit = !!props.id
const hours = Array.from({ length: 24 }, (_, i) => ({
  label: i.toString().padStart(2, '0') + ':00',
  value: i,
}))

const { get, create, update, default_project } = useProjects()

const title = props.id ? `Редактировать проект` : 'Создать проект'

useTitle(title)

const actionTitle = props.id ? 'Сохранить' : 'Создать'
const toastTitle = props.id ? `Успешно сохранено` : 'Проект создан'

const state = reactive<ProjectInSchema>({} as ProjectInSchema)

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
    router.back()
  } else {
    await update(props.id, data)
  }
}

onMounted(async () => {
  if (props.id) {
    const project = await get(props.id)
    Object.assign(state, parse(projectInSchema, project))
  } else {
    const def_project = await default_project()
    Object.assign(state, parse(projectInSchema, def_project))
  }
})
</script>
