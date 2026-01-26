<template>
  <div class="flex gap-4 pt-8">
    <!-- Календарь -->
    <div class="w-96">
      <UCalendar
        v-model="selectedDate"
        locale="ru"
        color="primary"
        size="md"
        @update:placeholder="onPlaceholderChange"
      >
        <template #day="{ day }">
          <UChip v-if="getDayCount(day) > 0" size="3xl" color="warning" :text="getDayCount(day)">
            {{ day.day }}
          </UChip>

          <span v-else class="opacity-40 cursor-not-allowed">
            {{ day.day }}
          </span>
        </template>
      </UCalendar>
    </div>

    <!-- Правая панель -->
    <div class="flex-1">
      <div v-if="!selectedDate" class="text-gray-500">Выберите день в календаре</div>

      <div v-else-if="dayMeetings.length === 0" class="text-gray-500">В этот день встреч нет</div>

      <UPageList v-else divide>
        <UPageCard
          v-for="meeting in dayMeetings"
          :key="meeting.id"
          variant="ghost"
          spotlight
          :title="`@${meeting.username}`"
          :description="formatMeetingTime(meeting.startAt, meeting.endAt)"
          class="cursor-pointer"
          @click="openModal(meeting)"
        />
      </UPageList>
    </div>
  </div>
  <MeetingModal
    v-if="selectedMeeting"
    :key="selectedMeeting.id"
    :meeting="selectedMeeting"
    v-model="isMeetingModalOpen"
  />
</template>

<script setup lang="ts">
import { ref, onMounted, watch, nextTick } from 'vue'
import { CalendarDate, type DateValue } from '@internationalized/date'
import { useDateFormat } from '@vueuse/core'
import { useMeetings } from '@/composables/use-meetings'
import type { DayMeeting, MeetingOut } from '@/types/openapi'
import MeetingModal from '@/components/dashboard/calendar/meeting-modal.vue'

/* ------------------------------------------------------------------ */
/* state */
/* ------------------------------------------------------------------ */

const selectedDate = ref<CalendarDate | undefined>(undefined)
const userSelectedDate = ref(false)

const selectedMeeting = ref<MeetingOut>()

const meetingsByDay = ref<DayMeeting[]>([])
const dayMeetings = ref<MeetingOut[]>([])

const currentYear = ref<number | null>(null)
const currentMonth = ref<number | null>(null)

const { getMonthMeetings, getDayMeetings } = useMeetings()

const isMeetingModalOpen = ref(false)

function openModal(item: MeetingOut) {
  selectedMeeting.value = undefined // сброс

  nextTick(() => {
    selectedMeeting.value = item
    isMeetingModalOpen.value = true
  })
}

/* ------------------------------------------------------------------ */
/* helpers */
/* ------------------------------------------------------------------ */

function formatMeetingTime(start: string, end: string) {
  const s = useDateFormat(start, 'HH:mm').value
  const e = useDateFormat(end, 'HH:mm').value
  return `${s}–${e}`
}

function getDayCount(day: DateValue): number {
  return (
    meetingsByDay.value.find(
      (m) =>
        new Date(m.date).getFullYear() === day.year &&
        new Date(m.date).getMonth() + 1 === day.month &&
        new Date(m.date).getDate() === day.day,
    )?.count ?? 0
  )
}

/* ------------------------------------------------------------------ */
/* loading */
/* ------------------------------------------------------------------ */

async function loadMonth(year: number, month: number) {
  currentYear.value = year
  currentMonth.value = month

  meetingsByDay.value = await getMonthMeetings(year, month)
  dayMeetings.value = []

  if (!userSelectedDate.value) {
    await selectNearestMeeting(year, month)
  }
}

async function loadDayMeetings(date: CalendarDate) {
  const iso = `${date.year}-${String(date.month).padStart(2, '0')}-${String(date.day).padStart(
    2,
    '0',
  )}`

  dayMeetings.value = await getDayMeetings(iso)
}

/* ------------------------------------------------------------------ */
/* selection logic */
/* ------------------------------------------------------------------ */

async function selectNearestMeeting(year: number, month: number) {
  if (!meetingsByDay.value.length) {
    selectedDate.value = undefined
    return
  }

  const today = new Date()

  const nearest = meetingsByDay.value
    .map((m) => new Date(m.date))
    .filter((d) => d.getFullYear() === year && d.getMonth() + 1 === month)
    .sort(
      (a, b) => Math.abs(a.getTime() - today.getTime()) - Math.abs(b.getTime() - today.getTime()),
    )[0]

  if (!nearest) return

  selectedDate.value = new CalendarDate(
    nearest.getFullYear(),
    nearest.getMonth() + 1,
    nearest.getDate(),
  )
}

/* ------------------------------------------------------------------ */
/* events */
/* ------------------------------------------------------------------ */

async function onPlaceholderChange(date: DateValue) {
  const monthChanged = date.year !== currentYear.value || date.month !== currentMonth.value

  if (!monthChanged) return

  userSelectedDate.value = false
  await loadMonth(date.year, date.month)
}

/* ------------------------------------------------------------------ */
/* watchers */
/* ------------------------------------------------------------------ */

watch(selectedDate, async (date) => {
  if (!date) return

  userSelectedDate.value = true
  const calendarDate = new CalendarDate(date.year, date.month, date.day)
  await loadDayMeetings(calendarDate)
})

/* ------------------------------------------------------------------ */
/* init */
/* ------------------------------------------------------------------ */

onMounted(async () => {
  const now = new Date()
  await loadMonth(now.getFullYear(), now.getMonth() + 1)
})
</script>
