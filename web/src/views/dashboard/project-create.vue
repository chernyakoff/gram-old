<template>
  <UDashboardPanel>
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
                  <UButton
                    icon="bx:show"
                    color="neutral"
                    variant="subtle"
                    v-if="disableSynonimize"
                  />
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

          <UFormField class="w-full mb-4" name="advancedMode">
            <UCheckbox v-model="state.advancedMode" label="Продвинутый режим" />
          </UFormField>
          <template v-if="!state.advancedMode">
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
          </template>
          <template v-else>
            <UTabs :items="tabs" variant="link" :ui="{ trigger: 'grow' }" class="gap-4 w-full">
              <template #edit>
                <UFormField name="prompt.role" class="w-full mb-4" label="Роль">
                  <MTextrarea
                    fullscreenTitle="Роль"
                    :rows="8"
                    v-model="state.prompt.role"
                    class="w-full"
                  />
                </UFormField>
                <UFormField name="prompt.context" class="w-full mb-4" label="Контекст">
                  <MTextrarea
                    fullscreenTitle="Контекст"
                    :rows="8"
                    v-model="state.prompt.context"
                    class="w-full"
                  />
                </UFormField>
                <UFormField name="prompt.init" class="w-full mb-4" label="INIT">
                  <MTextrarea
                    fullscreenTitle="INIT"
                    :rows="8"
                    v-model="state.prompt.init"
                    class="w-full"
                  />
                </UFormField>
                <UFormField name="prompt.engage" class="w-full mb-4" label="ENGAGE">
                  <MTextrarea
                    fullscreenTitle="ENGAGE"
                    :rows="8"
                    v-model="state.prompt.engage"
                    class="w-full"
                  />
                </UFormField>
                <UFormField name="prompt.offer" class="w-full mb-4" label="OFFER">
                  <MTextrarea
                    fullscreenTitle="OFFER"
                    :rows="8"
                    v-model="state.prompt.offer"
                    class="w-full"
                  />
                </UFormField>
                <UFormField name="prompt.closing" class="w-full mb-4" label="CLOSING">
                  <MTextrarea
                    fullscreenTitle="CLOSING"
                    :rows="8"
                    v-model="state.prompt.closing"
                    class="w-full"
                  />
                </UFormField>
                <UFormField name="prompt.instruction" class="w-full mb-4" label="Инструкции">
                  <MTextrarea
                    fullscreenTitle="Инструкции"
                    :rows="8"
                    v-model="state.prompt.instruction"
                    class="w-full"
                  />
                </UFormField>
                <UFormField name="prompt.rules" class="w-full mb-4" label="Правила">
                  <MTextrarea
                    fullscreenTitle="Правила"
                    :rows="8"
                    v-model="state.prompt.rules"
                    class="w-full"
                  />
                </UFormField>
                <UFormField name="skipOptions" class="w-full mb-4" label="Пропуск этапов">
                  <div class="flex gap-6 mt-4">
                    <UCheckbox
                      v-model="state.skipOptions.engage"
                      name="skipOptions.engage"
                      label="Engage"
                    />
                    <UCheckbox
                      v-model="state.skipOptions.offer"
                      name="skipOptions.offer"
                      label="Offer"
                    />
                    <UCheckbox
                      v-model="state.skipOptions.closing"
                      name="skipOptions.closing"
                      label="Closing"
                    />
                  </div>
                </UFormField>
              </template>
              <template #json>
                <div class="space-y-4 mb-4">
                  <UFormField label="JSON промпта" class="w-full">
                    <UTextarea
                      :rows="20"
                      v-model="jsonText"
                      placeholder='{"role": "...", "context": "...", ...}'
                      class="w-full font-mono text-sm"
                    />
                  </UFormField>
                  <div class="flex gap-2">
                    <UButton
                      label="Обновить промпт из JSON"
                      color="primary"
                      @click="updatePromptFromJson"
                    />
                    <UButton
                      label="Копировать JSON"
                      variant="outline"
                      color="neutral"
                      @click="copyJsonToClipboard"
                    />
                  </div>
                  <div v-if="jsonError" class="text-red-500 text-sm">
                    {{ jsonError }}
                  </div>
                </div>
              </template>
            </UTabs>
          </template>
        </div>

        <div class="flex items-center gap-10 justify-between w-full"></div>
      </UForm>
    </template>
  </UDashboardPanel>

  <BlockingModal
    title="Генерация промпта"
    text="Генерация промпта для вашего проекта займёт 1-2 минуты. Пожалуйста, не закрывайте страницу и дождитесь завершения процесса."
    :open="isGenerating"
  />
  <BlockingModal
    title="Рандомизирую"
    text="Дождитесь окончания рандомизации"
    :open="isRandomizing"
  />
</template>
<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useTitle } from '@vueuse/core'
import { useProjects } from '@/composables/use-projects'
import * as v from 'valibot'
import { projectInSchema, promptInSchema, type ProjectInSchema } from '@/schemas/projects'
import type { ProjectIn } from '@/types/openapi'
import type { FormSubmitEvent, TabsItem } from '@nuxt/ui'

import { useTemplateRef } from 'vue'
import { useBackgroundJobs } from '@/stores/jobs-store'
import MTextrarea from '@/components/shared/m-textrarea.vue'
import BlockingModal from '@/components/shared/blocking-modal.vue'

const jobsStore = useBackgroundJobs()

import { useRouter } from 'vue-router'
import { generateMessage } from '@/utils/prompt'

const toast = useToast()
const form = useTemplateRef('form')

const tabs = [
  { label: 'Редактирование', icon: 'bx:edit', slot: 'edit' as const },
  { label: 'JSON', icon: 'bx:code-curly', slot: 'json' as const },
] satisfies TabsItem[]

const router = useRouter()

const props = defineProps<{ id?: string }>()
const id = props.id ? Number(props.id) : undefined

const isGenerating = ref(false)
const isRandomizing = ref(false)

const jsonText = ref('')
const jsonError = ref('')

const hours = Array.from({ length: 24 }, (_, i) => ({
  label: i.toString().padStart(2, '0') + ':00',
  value: i,
}))

const disableSynonimize = computed(() => {
  // Ищем текст вида {что-то|что-то}
  const regex = /\{[^{}|]+\|[^{}]+\}/
  return regex.test(state.firstMessage)
})

const { get, create, update, default_project, synonimize } = useProjects()

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
  advancedMode: false,
  premiumRequired: true,
  skipOptions: {
    engage: false,
    offer: false,
    closing: false,
  },
  brief: {
    description: '',
    offer: '',
    client: '',
    pains: '',
    advantages: '',
    mission: '',
    focus: '',
  },
  prompt: {
    role: '',
    context: '',
    init: '',
    engage: '',
    offer: '',
    closing: '',
    instruction: '',
    rules: '',
  },
})

// Синхронизируем JSON с state.prompt
watch(
  () => state.prompt,
  (newPrompt) => {
    if (state.advancedMode) {
      jsonText.value = JSON.stringify(newPrompt, null, 2)
    }
  },
  { deep: true },
)

// Обновляем JSON при включении продвинутого режима
watch(
  () => state.advancedMode,
  (isAdvanced) => {
    if (isAdvanced) {
      jsonText.value = JSON.stringify(state.prompt, null, 2)
    }
  },
)

const updatePromptFromJson = () => {
  try {
    jsonError.value = ''
    const parsed = JSON.parse(jsonText.value)

    // Валидация с помощью valibot
    const result = v.safeParse(promptInSchema, parsed)

    if (result.success) {
      // Обновляем state.prompt
      Object.assign(state.prompt, result.output)

      toast.add({
        title: 'Промпт обновлён',
        description: 'Промпт успешно обновлён из JSON',
        color: 'success',
      })
    } else {
      // Форматируем ошибки валидации с помощью flatten
      const flattened = v.flatten<typeof promptInSchema>(result.issues)
      const errors = Object.entries(flattened.nested || {})
        .map(([key, messages]) => `${key}: ${messages?.join(', ')}`)
        .filter(Boolean)
        .join('; ')

      jsonError.value = errors || flattened.root?.join('; ') || 'Ошибка валидации'

      toast.add({
        title: 'Ошибка валидации',
        description: jsonError.value,
        color: 'error',
      })
    }
  } catch (error) {
    jsonError.value = error instanceof Error ? error.message : 'Ошибка парсинга JSON'
    toast.add({
      title: 'Ошибка',
      description: jsonError.value,
      color: 'error',
    })
  }
}

const copyJsonToClipboard = async () => {
  try {
    await navigator.clipboard.writeText(jsonText.value)
    toast.add({
      title: 'Скопировано',
      description: 'JSON скопирован в буфер обмена',
      color: 'success',
    })
  } catch {
    toast.add({
      title: 'Ошибка',
      description: 'Не удалось скопировать в буфер обмена',
      color: 'error',
    })
  }
}

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

  if (workflowId != 'NONE') {
    // Показываем модальное окно
    isGenerating.value = true

    jobsStore.add({
      id: workflowId,
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

        // Возвращаемся назад
        router.back()
      },
    })
  } else {
    toast.add({
      title: toastTitle,
      color: 'success',
    })
    router.back()
  }
}

onMounted(async () => {
  if (id) {
    const project = await get(id)
    Object.assign(state, project)
  } else {
    const def_project = await default_project()

    Object.assign(state, def_project)
  }
})

const doSynonimize = async () => {
  isRandomizing.value = true
  const { text } = await synonimize({ text: state.firstMessage })
  state.firstMessage = text
  isRandomizing.value = false
}
</script>
