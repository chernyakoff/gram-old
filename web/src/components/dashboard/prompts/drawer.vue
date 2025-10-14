<template>
  <UDrawer direction="right" :title="title" class="w-160" :handle="false" v-model:open="open">
    <template #body>
      <UForm ref="form" :schema="promptFormSchema" :state="state" @submit="onSubmit">
        <UFormField label="Наименование" name="name" class="mb-4">
          <UInput v-model="state.name" size="md" class="w-full" />
        </UFormField>

        <UFormField name="projectId" label="Выберите проект">
          <USelectMenu
            v-model="state.projectId"
            :items="projects"
            class="w-full"
            value-key="value"
          />
        </UFormField>
        <UAccordion :items="accordionItems" trailing-icon="i-lucide-arrow-down">
          <template #role>
            <UFormField name="role">
              <UTextarea
                v-model="state.role"
                placeholder="Ты выступаешь как [роль: эксперт по X, наставник, редактор текста, программист и т. д.]."
                class="w-full h-full resize-none"
                :rows="15"
              />
            </UFormField>
          </template>
          <template #instruction>
            <UFormField name="instruction">
              <UTextarea
                v-model="state.instruction"
                placeholder="Твоя задача: [чётко, что нужно сделать]."
                class="w-full h-full resize-none"
                :rows="15"
              />
            </UFormField>
          </template>
          <template #context>
            <UFormField name="context">
              <UTextarea
                v-model="state.context"
                placeholder="Учитывай, что: [факты, условия, вводные данные]."
                class="w-full h-full resize-none"
                :rows="15"
              />
            </UFormField>
          </template>
          <template #examples>
            <UFormField name="examples">
              <UTextarea
                v-model="state.examples"
                placeholder="Пример ожидаемого ответа."
                class="w-full h-full resize-none"
                :rows="15"
              />
            </UFormField>
          </template>
          <template #constraints>
            <UFormField name="constraints">
              <UTextarea
                v-model="state.constraints"
                placeholder="Формат: [какой стиль/структура/ограничения: без воды, на русском, до 500 символов и т. п.]."
                class="w-full h-full resize-none"
                :rows="15"
              />
            </UFormField>
          </template>
          <template #outputFormat>
            <UFormField name="outputFormat">
              <UTextarea
                v-model="state.outputFormat"
                placeholder="На выходе дай [конкретный тип результата: список, код, таблицу, текст]."
                class="w-full h-full resize-none"
                :rows="15"
              />
            </UFormField>
          </template>
        </UAccordion>
      </UForm>
    </template>
    <template #footer>
      <UButton
        label="Сохранить"
        :disabled="!form?.errors"
        @click="doSubmit"
        color="neutral"
        class="justify-center"
      />
      <UButton
        label="Закрыть"
        color="neutral"
        variant="outline"
        class="justify-center"
        @click="$emit('update:open', false)"
      />
    </template>
  </UDrawer>
</template>
<script setup lang="ts">
import { usePrompts } from '@/composables/use-prompts'

import type { FormSubmitEvent, SelectMenuItem } from '@nuxt/ui'
import { ref, useTemplateRef } from 'vue'
import * as v from 'valibot'
import { reactive, watch, computed } from 'vue'
import { parsePromptIn, promptFormSchema, type PromptFormSchema } from '@/schemas/prompts'
import { useProjects } from '@/composables/use-projects'
import type { AccordionItem } from '@nuxt/ui'

const accordionItems = [
  {
    label: 'Роль',
    icon: 'lucide:user',
    slot: 'role' as const,
  },
  {
    label: 'Инструкции',
    icon: 'lucide:command',
    slot: 'instruction' as const,
  },
  {
    label: 'Контекст',
    icon: 'lucide:layers',
    slot: 'context' as const,
  },
  {
    label: 'Пример',
    icon: 'lucide:book-open',
    slot: 'examples' as const,
  },
  {
    label: 'Ограничения',
    icon: 'lucide:shield-off',
    slot: 'constraints' as const,
  },
  {
    label: 'Результат',
    icon: 'lucide:terminal',
    slot: 'outputFormat' as const,
  },
] satisfies AccordionItem[]

const open = defineModel<boolean>('open', { default: false })
const form = useTemplateRef('form')
const title = computed(() => (promptId ? `Редактировать` : 'Создать'))
const projects = ref<SelectMenuItem[]>([])

const { promptId } = defineProps<{
  promptId?: number
}>()

const emit = defineEmits<{
  (e: 'update:open', value: boolean): void
  (e: 'closed'): void
}>()

const getEmptyState = (): PromptFormSchema => ({
  name: '',
  projectId: undefined,
  role: '',
  instruction: '',
  context: '',
  examples: '',
  constraints: '',
  outputFormat: '',
})

const state = reactive<PromptFormSchema>(getEmptyState())

const { get, create, update } = usePrompts()
const { list: getList } = useProjects()

const doSubmit = async () => {
  await form.value?.submit()
}

const onSubmit = async (event: FormSubmitEvent<PromptFormSchema>) => {
  const data = parsePromptIn(event.data)
  if (!promptId) {
    await create(data)
  } else {
    await update(promptId, data)
  }
  open.value = false
  emit('closed')
}

watch(
  [open, () => promptId],
  async ([isOpen, id]) => {
    let data: PromptFormSchema
    if (isOpen && id) {
      const dto = await get(id)
      data = v.parse(promptFormSchema, { ...dto, projectId: dto.project?.id })
      Object.assign(state, data)
    } else {
      Object.assign(state, getEmptyState())
    }
    if (projects.value.length === 0) {
      projects.value = (await getList()).map((m) => ({
        label: m.name,
        value: m.id,
      }))
    }
  },
  { immediate: true },
)
</script>
