<template>
  <UDashboardPanel id="home">
    <template #header>
      <UDashboardNavbar :title="title" :ui="{ right: 'gap-3' }">
        <template #leading>
          <UDashboardSidebarCollapse />
        </template>
      </UDashboardNavbar>
    </template>
    <template #body>
      <div class="grid gap-4 grid-cols-1 md:grid-cols-2 lg:grid-cols-4">
        <div>
          <UPopover class="w-full">
            <UButton color="neutral" variant="subtle" icon="i-lucide-calendar">
              <template v-if="range.start">
                <template v-if="range.end">
                  {{ df.format(range.start.toDate(getLocalTimeZone())) }} -
                  {{ df.format(range.end.toDate(getLocalTimeZone())) }}
                </template>

                <template v-else>
                  {{ df.format(range.start.toDate(getLocalTimeZone())) }}
                </template>
              </template>
              <template v-else>Pick a date</template>
            </UButton>
            <template #content>
              <UCalendar v-model="range" class="p-2" :number-of-months="2" range />
            </template>
          </UPopover>
        </div>
        <div>
          <USelectMenu
            placeholder="Выберите проект"
            v-model="projectId"
            :items="projects"
            class="w-full"
            value-key="id"
            label-key="name"
          />
        </div>
        <div>
          <USelectMenu
            placeholder="Выберите аккаунт"
            v-model="accountId"
            :items="accounts"
            class="w-full"
            value-key="id"
            label-key="name"
          />
        </div>
        <div>
          <USelectMenu
            placeholder="Выберите рассылку"
            v-model="mailingId"
            :items="mailings"
            class="w-full"
            value-key="id"
            label-key="name"
          />
        </div>
      </div>
      <div :class="containerClass" class="w-full gap-4 transition-all duration-500">
        <UCard
          :class="[firstCardClass, 'bg-gray-100 dark:bg-gray-800']"
          class="relative transition-all duration-500"
        >
          <div class="absolute top-2 right-2">
            <button @click="toggleFullWidth" class="btn btn-sm">🔄</button>
          </div>

          <AreaChart :stats-data="statsData" :start-date="startDate" />
        </UCard>

        <UCard
          :class="[secondCardClass, 'bg-gray-100 dark:bg-gray-800']"
          class="transition-all duration-500"
        >
          <BarChart :stats-data="statsData" />
        </UCard>
      </div>
    </template>
  </UDashboardPanel>
</template>
<script setup lang="ts">
import { useAccounts } from '@/composables/use-accounts'
import { useMailings } from '@/composables/use-mailings'
import { useProjects } from '@/composables/use-projects'
import type {
  AccountListOut,
  MailingListOut,
  ProjectBase,
  StatsIn,
  StatsOut,
} from '@/types/openapi'
import AreaChart from '@/components/dashboard/index/area-chart.vue'
import BarChart from '@/components/dashboard/index/bar-chart.vue'
import { useTitle } from '@vueuse/core'
import { computed, onMounted, ref, shallowRef, watch } from 'vue'
import { CalendarDate, DateFormatter, getLocalTimeZone } from '@internationalized/date'
import { useStats } from '@/composables/use-stats'

const df = new DateFormatter('ru-RU', {
  dateStyle: 'short',
})

const title = 'Дашборд'
useTitle(title)

const { list: getProjectList } = useProjects()
const { list: getMailingList } = useMailings()
const { list: getAccountList } = useAccounts()
const { getStats } = useStats()

const projects = ref<ProjectBase[]>()
const mailings = ref<MailingListOut[]>()
const accounts = ref<AccountListOut[]>()

const projectId = ref<number | undefined>()

const accountId = ref<number | undefined>()

const mailingId = ref<number | undefined>()
const fullWidth = ref(false)

const toggleFullWidth = () => {
  fullWidth.value = !fullWidth.value
}

// контейнер: flex-row или flex-col
const containerClass = computed(() => (fullWidth.value ? 'flex flex-col' : 'flex flex-row'))

// первый UCard: ширина 70% или 100%
const firstCardClass = computed(() => (fullWidth.value ? 'w-full' : 'w-[70%]'))

// второй UCard: ширина 30% или 100%
const secondCardClass = computed(() => (fullWidth.value ? 'w-full mt-4' : 'w-[30%]'))

const now = new Date()
const oneMonthAgo = new Date()
oneMonthAgo.setMonth(now.getMonth() - 1)

const statsData = ref<StatsOut>({
  init: [],
  engage: [],
  offer: [],
  closing: [],
})

const range = shallowRef({
  start: new CalendarDate(
    oneMonthAgo.getFullYear(),
    oneMonthAgo.getMonth() + 1,
    oneMonthAgo.getDate(),
  ),
  end: new CalendarDate(now.getFullYear(), now.getMonth() + 1, now.getDate()),
})

const startDate = computed(() =>
  range.value.start.toDate(getLocalTimeZone()).toISOString().slice(0, 10),
)

onMounted(async () => {
  projects.value = await getProjectList()
  mailings.value = await getMailingList()
  accounts.value = await getAccountList()
  statsData.value = await getStats(getPayload())
})

const getPayload = (): StatsIn => ({
  dateFrom: range.value.start.toDate(getLocalTimeZone()).toISOString().slice(0, 10),
  dateTo: range.value.end.toDate(getLocalTimeZone()).toISOString().slice(0, 10),
  projectId: projectId.value ?? null,
  accountId: accountId.value ?? null,
  mailingId: mailingId.value ?? null,
})

watch(
  [range, projectId, accountId, mailingId],
  async () => {
    if (!range.value.start || !range.value.end) return
    statsData.value = await getStats(getPayload())
  },
  { deep: true },
)
</script>
