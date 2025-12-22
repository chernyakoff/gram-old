<template>
  <UDashboardPanel id="settings">
    <template #header>
      <UDashboardNavbar :title="title" :ui="{ right: 'gap-3' }">
        <template #leading>
          <UDashboardSidebarCollapse />
        </template>
        <template #right>
          <UButton
            size="lg"
            type="submit"
            label="Сохранить"
            color="primary"
            :loading="loading"
            @click="doSubmit"
          />
        </template>
      </UDashboardNavbar>
    </template>
    <template #body>
      <UForm ref="form" :schema="aiModelSchema" :state="state" @submit="onSubmit">
        <div class="min-w-[800px] max-w-4xl mx-auto">
          <UTabs :items="tabs" variant="link" :ui="{ trigger: 'grow' }" class="gap-4">
            <template #aiModel>
              <div class="space-y-6 p-6">
                <div>
                  <h3 class="text-lg font-semibold mb-2">Выбор AI модели</h3>
                  <p class="text-sm text-gray-500 dark:text-gray-400 mb-4">
                    Выберите модель для обработки запросов. Цены указаны в рублях.
                  </p>
                </div>

                <!-- Hidden field для формы -->
                <input type="hidden" v-model="state.id" />

                <!-- Выбранная модель -->
                <UCard
                  v-if="selectedModel"
                  class="bg-primary-50 dark:bg-primary-950 border-2 border-primary-500"
                >
                  <div class="flex items-start gap-4">
                    <div class="flex-shrink-0">
                      <UIcon name="i-heroicons-check-circle" class="h-8 w-8 text-primary-500" />
                    </div>
                    <div class="flex-1">
                      <div class="flex items-center gap-2 mb-1">
                        <h4 class="font-semibold text-lg">{{ selectedModel.name }}</h4>
                        <UBadge color="primary" variant="subtle" size="xs">Выбрано</UBadge>
                      </div>
                      <p
                        class="text-sm text-gray-600 dark:text-gray-300 mb-3"
                        v-html="selectedModel.description"
                      ></p>
                      <div class="flex flex-wrap gap-4 text-sm">
                        <div class="flex items-center gap-2">
                          <UIcon
                            name="i-heroicons-arrow-up-circle"
                            class="h-4 w-4 text-primary-500"
                          />
                          <span class="text-gray-700 dark:text-gray-200">
                            Prompt:
                            <strong>{{ formatPrice(selectedModel.promptPrice) }} ₽</strong>
                            /1K токенов
                          </span>
                        </div>
                        <div class="flex items-center gap-2">
                          <UIcon
                            name="i-heroicons-arrow-down-circle"
                            class="h-4 w-4 text-primary-500"
                          />
                          <span class="text-gray-700 dark:text-gray-200">
                            Completion:
                            <strong>{{ formatPrice(selectedModel.completionPrice) }} ₽</strong>
                            /1K токенов
                          </span>
                        </div>
                      </div>
                    </div>
                  </div>
                </UCard>

                <!-- Поиск -->
                <div class="relative">
                  <UInput
                    v-model="searchQuery"
                    icon="i-heroicons-magnifying-glass"
                    placeholder="Поиск модели..."
                    size="lg"
                  />
                </div>

                <!-- Список моделей -->
                <div v-if="modelsLoading" class="flex justify-center py-8">
                  <UIcon name="i-heroicons-arrow-path" class="animate-spin h-8 w-8" />
                </div>

                <div v-else-if="filteredModels.length === 0" class="text-center py-8 text-gray-500">
                  {{ searchQuery ? 'Модели не найдены' : 'Нет доступных моделей' }}
                </div>

                <div v-else class="space-y-2">
                  <p class="text-sm text-gray-500 dark:text-gray-400 mb-3">
                    Найдено моделей: {{ filteredModels.length }}
                  </p>

                  <div class="space-y-2 max-h-[600px] overflow-y-auto pr-2">
                    <UCard
                      v-for="model in filteredModels"
                      :key="model.id"
                      class="cursor-pointer transition-all hover:shadow-md !ring-0 !border-0"
                      :class="{
                        'bg-primary-50 dark:bg-primary-900': state.id === model.id,
                        'hover:bg-gray-50 dark:hover:bg-gray-800': state.id !== model.id,
                      }"
                      @click="selectModel(model.id)"
                    >
                      <div class="flex items-start gap-3">
                        <div class="flex-shrink-0 mt-1">
                          <div
                            class="w-5 h-5 rounded-full border-2 flex items-center justify-center"
                            :class="{
                              'border-primary-500 bg-primary-500': state.id === model.id,
                              'border-gray-300 dark:border-gray-600': state.id !== model.id,
                            }"
                          >
                            <UIcon
                              v-if="state.id === model.id"
                              name="i-heroicons-check"
                              class="h-3 w-3 text-white"
                            />
                          </div>
                        </div>
                        <div class="flex-1 min-w-0">
                          <div class="flex items-center gap-2 mb-1">
                            <h5 class="font-medium">{{ model.name }}</h5>
                          </div>
                          <p
                            class="text-sm text-gray-600 dark:text-gray-400 mb-2 line-clamp-2"
                            v-html="model.description"
                          ></p>
                          <div
                            class="flex flex-wrap gap-3 text-xs text-gray-500 dark:text-gray-400"
                          >
                            <span class="flex items-center gap-1">
                              <UIcon name="i-heroicons-arrow-up-circle-mini" class="h-3 w-3" />
                              {{ formatPrice(model.promptPrice) }} ₽
                            </span>
                            <span class="flex items-center gap-1">
                              <UIcon name="i-heroicons-arrow-down-circle-mini" class="h-3 w-3" />
                              {{ formatPrice(model.completionPrice) }} ₽
                            </span>
                            <span class="text-gray-400">•</span>
                            <span class="font-mono">{{ model.id }}</span>
                          </div>
                        </div>
                      </div>
                    </UCard>
                  </div>
                </div>
              </div>
            </template>
          </UTabs>
        </div>
      </UForm>
    </template>
  </UDashboardPanel>
</template>

<script setup lang="ts">
import { useTitle } from '@vueuse/core'
import type { FormSubmitEvent, TabsItem } from '@nuxt/ui'

import { computed, onMounted, reactive, ref } from 'vue'
import { aiModelSchema, type AiModelSchema } from '@/schemas/settings'
import { useTemplateRef } from 'vue'
import { useAiModels } from '@/composables/use-ai-models'
import type { AiModelOut } from '@/types/openapi'

const { save, get, selected, loading } = useAiModels()

const title = 'Настройки'
useTitle(title)

const tabs = [
  { label: 'AI Модель', icon: 'i-heroicons-cpu-chip', slot: 'aiModel' as const },
] satisfies TabsItem[]

const form = useTemplateRef('form')
const modelsLoading = ref(false)

const searchQuery = ref('')

const models = ref<AiModelOut[]>([])

const state = reactive({
  id: 'openai/gpt-5.2-chat',
})

const toast = useToast()

const formatPrice = (price: string): string => {
  const num = parseFloat(price) * 1000 // Умножаем на 1000 для цены за 1K токенов
  return num.toFixed(4)
}

const selectModel = (modelId: string) => {
  state.id = modelId
}

const selectedModel = computed(() => {
  return models.value.find((m) => m.id === state.id)
})

const filteredModels = computed(() => {
  if (!searchQuery.value) {
    return models.value
  }

  const query = searchQuery.value.toLowerCase()
  return models.value.filter(
    (model) =>
      model.name.toLowerCase().includes(query) ||
      model.id.toLowerCase().includes(query) ||
      model.description.toLowerCase().includes(query),
  )
})

const doSubmit = async () => {
  await form.value?.submit()
}

onMounted(async () => {
  modelsLoading.value = true
  try {
    const [modelsData, selectedModel] = await Promise.all([get(), selected()])

    models.value = modelsData

    if (selectedModel) {
      state.id = selectedModel.id
    }
  } finally {
    modelsLoading.value = false
  }
})

const onSubmit = async (event: FormSubmitEvent<AiModelSchema>) => {
  const success = await save(event.data)
  if (success) {
    toast.add({
      title: 'Модель сохранена',
      color: 'success',
    })
    // Опционально: можно перезагрузить данные или показать уведомление
  } else {
    toast.add({
      title: 'Не удалось сохранить модель',
      color: 'error',
    })
  }
}
</script>
<style scoped>
.line-clamp-2 {
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
</style>
