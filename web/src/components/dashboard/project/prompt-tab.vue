<template>
  <UForm ref="form" :schema="promptSchema" :state="state" @submit="onSubmit">
    <div class="min-w-[800px] max-w-4xl mx-auto">
      <UTabs :items="tabs" variant="link" :ui="{ trigger: 'grow' }" class="gap-4 w-full">
        <template #edit>
          <UFormField name="role" class="w-full mb-4" label="Роль">
            <MTextrarea fullscreenTitle="Роль" :rows="8" v-model="state.role" class="w-full" />
          </UFormField>
          <UFormField name="context" class="w-full mb-4" label="Контекст">
            <MTextrarea
              fullscreenTitle="Контекст"
              :rows="8"
              v-model="state.context"
              class="w-full"
            />
          </UFormField>
          <UFormField name="init" class="w-full mb-4" label="INIT">
            <MTextrarea fullscreenTitle="INIT" :rows="8" v-model="state.init" class="w-full" />
          </UFormField>
          <UFormField name="engage" class="w-full mb-4" label="ENGAGE">
            <MTextrarea fullscreenTitle="ENGAGE" :rows="8" v-model="state.engage" class="w-full" />
          </UFormField>
          <UFormField name="offer" class="w-full mb-4" label="OFFER">
            <MTextrarea fullscreenTitle="OFFER" :rows="8" v-model="state.offer" class="w-full" />
          </UFormField>
          <UFormField name="closing" class="w-full mb-4" label="CLOSING">
            <MTextrarea
              fullscreenTitle="CLOSING"
              :rows="8"
              v-model="state.closing"
              class="w-full"
            />
          </UFormField>
          <UFormField name="instruction" class="w-full mb-4" label="Инструкции">
            <MTextrarea
              fullscreenTitle="Инструкции"
              :rows="8"
              v-model="state.instruction"
              class="w-full"
            />
          </UFormField>
          <UFormField name="rules" class="w-full mb-4" label="Правила">
            <MTextrarea fullscreenTitle="Правила" :rows="8" v-model="state.rules" class="w-full" />
          </UFormField>
          <UFormField name="skipOptions" class="w-full mb-4" label="Пропуск этапов">
            <div class="flex gap-6 mt-4">
              <UCheckbox
                v-model="state.skipOptions.engage"
                name="skipOptions.engage"
                label="Engage"
              />
              <UCheckbox v-model="state.skipOptions.offer" name="skipOptions.offer" label="Offer" />
              <UCheckbox
                v-model="state.skipOptions.closing"
                name="skipOptions.closing"
                label="Closing"
              />
            </div>
          </UFormField>
          <UButton type="submit">Сохранить</UButton>
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
    </div>
  </UForm>
</template>
<script lang="ts" setup>
import * as v from 'valibot'
import type { FormSubmitEvent, TabsItem } from '@nuxt/ui'
import MTextrarea from '@/components/shared/m-textrarea.vue'
import { onMounted, reactive, ref, watchEffect } from 'vue'
import { useProjects } from '@/composables/use-projects'

const { getPrompt, savePrompt } = useProjects()

const { projectId } = defineProps<{
  projectId: number
}>()
const toast = useToast()

const jsonText = ref('')
const jsonError = ref('')

const tabs = [
  { label: 'Редактирование', icon: 'bx:edit', slot: 'edit' as const },
  { label: 'JSON', icon: 'bx:code-curly', slot: 'json' as const },
] satisfies TabsItem[]

const textSchema = v.pipe(
  v.string('должно быть строкой'),
  v.nonEmpty('обязательное поле'),
  v.minLength(32, 'должно содержать хотя бы 32 символа'),
)
const skipOptionsSchema = v.object({
  engage: v.boolean(),
  offer: v.boolean(),
  closing: v.boolean(),
})

const promptSchema = v.object({
  role: textSchema,
  context: textSchema,
  init: textSchema,
  engage: textSchema,
  offer: textSchema,
  closing: textSchema,
  instruction: textSchema,
  rules: textSchema,
  skipOptions: skipOptionsSchema,
})

type PromptSchema = v.InferOutput<typeof promptSchema>

const state = reactive<PromptSchema>({
  role: '',
  context: '',
  init: '',
  engage: '',
  offer: '',
  closing: '',
  instruction: '',
  rules: '',
  skipOptions: {
    engage: false,
    offer: false,
    closing: false,
  },
})

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

const updatePromptFromJson = () => {
  try {
    jsonError.value = ''
    const parsed = JSON.parse(jsonText.value)

    // Валидация с помощью valibot
    const result = v.safeParse(promptSchema, parsed)

    if (result.success) {
      // Обновляем state.prompt
      Object.assign(state, result.output)

      toast.add({
        title: 'Промпт обновлён',
        description: 'Промпт успешно обновлён из JSON',
        color: 'success',
      })
    } else {
      // Форматируем ошибки валидации с помощью flatten
      const flattened = v.flatten<typeof promptSchema>(result.issues)
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

watchEffect(() => {
  jsonText.value = JSON.stringify(state, null, 2)
})

onMounted(async () => {
  const response = await getPrompt(projectId)
  Object.assign(state, response)
})

const onSubmit = async (event: FormSubmitEvent<PromptSchema>) => {
  await savePrompt(projectId, event.data)
  toast.add({
    title: 'Промпт успешно сохранен',
    color: 'success',
  })
}
</script>
