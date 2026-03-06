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
            type="button"
            label="Сохранить"
            color="primary"
            :loading="aiLoading"
            @click="doSubmitAi"
          />
        </template>
      </UDashboardNavbar>
    </template>
    <template #body>
      <div class="min-w-[800px] max-w-4xl mx-auto">
        <UTabs :items="tabs" variant="link" :ui="{ trigger: 'grow' }" class="gap-4">
          <template #aiModel>
            <UForm ref="aiForm" :schema="aiModelSchema" :state="aiState" @submit="onAiSubmit">
              <div class="space-y-6 p-6">
                <div>
                  <h3 class="text-lg font-semibold mb-2">Выбор AI модели</h3>
                  <p class="text-sm text-gray-500 dark:text-gray-400 mb-4">
                    Выберите модель для обработки запросов. Цены указаны в рублях.
                  </p>
                </div>

                <input type="hidden" v-model="aiState.id" />

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

                <div class="relative">
                  <UInput
                    v-model="searchQuery"
                    icon="i-heroicons-magnifying-glass"
                    placeholder="Поиск модели..."
                    size="lg"
                  />
                </div>

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
                        'bg-primary-50 dark:bg-primary-900': aiState.id === model.id,
                        'hover:bg-gray-50 dark:hover:bg-gray-800': aiState.id !== model.id,
                      }"
                      @click="selectModel(model.id)"
                    >
                      <div class="flex items-start gap-3">
                        <div class="flex-shrink-0 mt-1">
                          <div
                            class="w-5 h-5 rounded-full border-2 flex items-center justify-center"
                            :class="{
                              'border-primary-500 bg-primary-500': aiState.id === model.id,
                              'border-gray-300 dark:border-gray-600': aiState.id !== model.id,
                            }"
                          >
                            <UIcon
                              v-if="aiState.id === model.id"
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
            </UForm>
          </template>

          <template #mobProxy>
            <div class="space-y-6 p-6">
              <div>
                <h3 class="text-lg font-semibold mb-2">Моб. Прокси</h3>
                <p class="text-sm text-gray-500 dark:text-gray-400 mb-4">
                  Один пользователь может хранить только одну мобильную прокси.
                </p>
              </div>

              <div v-if="!mobProxyFormVisible">
                <UButton
                  label="Добавить"
                  icon="i-lucide-plus"
                  color="primary"
                  @click="onAddMobProxy"
                />
              </div>

              <UForm
                v-else
                ref="mobProxyForm"
                :schema="mobProxyFormSchema"
                :state="mobProxyState"
                @submit="onSubmit"
              >
                <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <UFormField label="Host" name="host">
                    <UInput v-model="mobProxyState.host" placeholder="127.0.0.1" />
                  </UFormField>

                  <UFormField label="Port" name="port">
                    <UInput v-model.number="mobProxyState.port" type="number" :min="1" />
                  </UFormField>

                  <UFormField label="Username" name="username">
                    <UInput v-model="mobProxyState.username" />
                  </UFormField>

                  <UFormField label="Password" name="password">
                    <UInput v-model="mobProxyState.password" type="password" />
                  </UFormField>

                  <UFormField label="Country" name="country">
                    <USelectMenu
                      v-model="mobProxyState.country"
                      :items="countries"
                      class="w-full"
                      :search-input="{
                        placeholder: 'Поиск...',
                        icon: 'bx:search',
                      }"
                    />
                  </UFormField>

                  <UFormField label="Active" name="active" class="flex items-end">
                    <USwitch v-model="mobProxyState.active" />
                  </UFormField>
                </div>

                <UFormField label="Change URL" name="changeUrl" class="mt-4">
                  <UInput v-model="mobProxyState.changeUrl" placeholder="https://..." />
                </UFormField>

                <div class="flex gap-2 mt-6">
                  <UButton
                    type="submit"
                    color="primary"
                    :loading="mobProxyLoading"
                    :disabled="mobProxyLoading"
                  >
                    Сохранить
                  </UButton>
                  <UButton
                    color="error"
                    variant="soft"
                    :loading="mobProxyLoading"
                    :disabled="mobProxyLoading"
                    @click="onDeleteMobProxy"
                  >
                    Удалить
                  </UButton>
                </div>
              </UForm>
            </div>
          </template>
        </UTabs>
      </div>
    </template>
  </UDashboardPanel>
</template>

<script setup lang="ts">
import { useTitle } from '@vueuse/core'
import type { FormSubmitEvent, TabsItem } from '@nuxt/ui'

import { computed, onMounted, reactive, ref } from 'vue'
import {
  aiModelSchema,
  mobProxyFormSchema,
  type AiModelSchema,
  type MobProxyFormSchema,
} from '@/schemas/settings'
import { useTemplateRef } from 'vue'
import { useAiModels } from '@/composables/use-ai-models'
import { useMobProxy } from '@/composables/use-mob-proxy'
import type { AiModelOut, MobProxyCreateIn, MobProxyOut, MobProxyUpdateIn } from '@/types/openapi'

const {
  save: saveAiModel,
  get: getAiModels,
  selected: getSelectedAiModel,
  loading: aiLoading,
} = useAiModels()
const {
  get: getMobProxy,
  create: createMobProxy,
  update: updateMobProxy,
  del: deleteMobProxy,
  loading: mobProxyLoading,
} = useMobProxy()

const title = 'Настройки'
useTitle(title)

const tabs = [
  { label: 'AI Модель', icon: 'i-heroicons-cpu-chip', slot: 'aiModel' as const },
  { label: 'Моб. Прокси', icon: 'i-lucide-smartphone', slot: 'mobProxy' as const },
] satisfies TabsItem[]

// prettier-ignore
const countries = [
  "AF","AX","AL","DZ","AS","AD","AO","AI","AQ","AG","AR","AM","AW","AU","AT",
  "AZ","BS","BH","BD","BB","BY","BE","BZ","BJ","BM","BT","BO","BQ","BA","BW",
  "BV","BR","IO","BN","BG","BF","BI","KH","CM","CA","CV","KY","CF","TD","CL",
  "CN","CX","CC","CO","KM","CG","CD","CK","CR","CI","HR","CU","CW","CY","CZ",
  "DK","DJ","DM","DO","EC","EG","SV","GQ","ER","EE","SZ","ET","FK","FO","FJ",
  "FI","FR","GF","PF","TF","GA","GM","GE","DE","GH","GI","GR","GL","GD","GP",
  "GU","GT","GG","GN","GW","GY","HT","HM","VA","HN","HK","HU","IS","IN","ID",
  "IR","IQ","IE","IM","IL","IT","JM","JP","JE","JO","KZ","KE","KI","KP","KR",
  "KW","KG","LA","LV","LB","LS","LR","LY","LI","LT","LU","MO","MG","MW","MY",
  "MV","ML","MT","MH","MQ","MR","MU","YT","MX","FM","MD","MC","MN","ME","MS",
  "MA","MZ","MM","NA","NR","NP","NL","NC","NZ","NI","NE","NG","NU","NF","MK",
  "MP","NO","OM","PK","PW","PS","PA","PG","PY","PE","PH","PN","PL","PT","PR",
  "QA","RE","RO","RU","RW","BL","SH","KN","LC","MF","PM","VC","WS","SM","ST",
  "SA","SN","RS","SC","SL","SG","SX","SK","SI","SB","SO","ZA","GS","SS","ES",
  "LK","SD","SR","SJ","SE","CH","SY","TW","TJ","TZ","TH","TL","TG","TK","TO",
  "TT","TN","TR","TM","TC","TV","UG","UA","AE","GB","UM","US","UY","UZ","VU",
  "VE","VN","VG","VI","WF","EH","YE","ZM","ZW"
]

const aiForm = useTemplateRef('aiForm')
const modelsLoading = ref(false)

const searchQuery = ref('')

const models = ref<AiModelOut[]>([])
const mobProxyId = ref<number | null>(null)
const mobProxyFormVisible = ref(false)

const aiState = reactive({
  id: 'openai/gpt-5.2-chat',
})

const getEmptyMobProxyState = (): MobProxyFormSchema => ({
  host: '',
  port: 1080,
  username: '',
  password: '',
  changeUrl: '',
  country: '',
  active: true,
})

const mobProxyState = reactive<MobProxyFormSchema>(getEmptyMobProxyState())

const toast = useToast()

const formatPrice = (price: string): string => {
  const num = parseFloat(price) * 1000
  return num.toFixed(4)
}

const selectModel = (modelId: string) => {
  aiState.id = modelId
}

const selectedModel = computed(() => {
  return models.value.find((m) => m.id === aiState.id)
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

const assignMobProxyState = (proxy: MobProxyOut) => {
  mobProxyState.host = proxy.host
  mobProxyState.port = proxy.port
  mobProxyState.username = proxy.username
  mobProxyState.password = proxy.password
  mobProxyState.changeUrl = proxy.changeUrl
  mobProxyState.country = proxy.country
  mobProxyState.active = proxy.active
}

const doSubmitAi = async () => {
  await aiForm.value?.submit()
}

onMounted(async () => {
  modelsLoading.value = true
  try {
    const [modelsData, selectedAiModel, mobProxy] = await Promise.all([
      getAiModels(),
      getSelectedAiModel(),
      getMobProxy(),
    ])

    models.value = modelsData

    if (selectedAiModel) {
      aiState.id = selectedAiModel.id
    }

    if (mobProxy) {
      mobProxyId.value = mobProxy.id
      mobProxyFormVisible.value = true
      assignMobProxyState(mobProxy)
    }
  } finally {
    modelsLoading.value = false
  }
})

const onAiSubmit = async (event: FormSubmitEvent<AiModelSchema>) => {
  const success = await saveAiModel(event.data)
  if (success) {
    toast.add({
      title: 'Модель сохранена',
      color: 'success',
    })
  } else {
    toast.add({
      title: 'Не удалось сохранить модель',
      color: 'error',
    })
  }
}

const onAddMobProxy = () => {
  mobProxyFormVisible.value = true
  if (!mobProxyId.value) {
    Object.assign(mobProxyState, getEmptyMobProxyState())
  }
}

const onSubmit = async (event: FormSubmitEvent<MobProxyFormSchema>) => {
  const payload = {
    ...event.data,
    country: event.data.country.toUpperCase(),
  }

  let result: MobProxyOut
  if (mobProxyId.value === null) {
    result = await createMobProxy(payload satisfies MobProxyCreateIn)
  } else {
    result = await updateMobProxy(payload satisfies MobProxyUpdateIn)
  }

  mobProxyId.value = result.id
  assignMobProxyState(result)
  mobProxyFormVisible.value = true
  toast.add({ title: 'Моб. прокси сохранена', color: 'success' })
}

const onDeleteMobProxy = async () => {
  if (mobProxyId.value === null) {
    mobProxyFormVisible.value = false
    return
  }

  await deleteMobProxy()
  mobProxyId.value = null
  mobProxyFormVisible.value = false
  Object.assign(mobProxyState, getEmptyMobProxyState())
  toast.add({ title: 'Моб. прокси удалена', color: 'success' })
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
