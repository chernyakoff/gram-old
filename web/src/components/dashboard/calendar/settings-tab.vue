<template>
  <div class="mx-auto w-max space-y-4 px-4 pt-4">
    <UFormField label="Расписание">
      <div class="flex items-center gap-2">
        <USelectMenu
          class="w-72"
          v-model="selectedCalendarId"
          :items="calendarItems"
          value-key="value"
          label-key="label"
          placeholder="Выберите расписание" />
        <UButton icon="i-heroicons-plus" color="primary" variant="soft" @click="createModalOpen = true" />
        <UButton
          icon="i-heroicons-trash"
          color="error"
          variant="soft"
          :disabled="calendarItems.length <= 1 || !selectedCalendarId"
          @click="deleteModalOpen = true" />
      </div>
    </UFormField>
    <UFormField label="Часовой пояс">
      <USelectMenu
        class="w-full mt-b"
        :search-input="{
          placeholder: 'Поиск...',
          icon: 'i-lucide-search',
        }"
        v-model="selectedTimezone"
        :items="timezones"
        virtualize
        value-key="value"
        label-key="label"
        searchable
        placeholder="Выберите таймзону" />
    </UFormField>
    <UFormField label="Длительность встречи (мин)">
      <UInputNumber v-model="selectedMeetingDuration" :step="10" :min="10" />
    </UFormField>
    <div class="text-sm mt-8">Недельное расписание</div>
    <div v-for="(day, dayIndex) in schedule" :key="dayIndex" class="space-y-1">
      <!-- Основная строка дня -->
      <div class="flex items-center gap-3">
        <!-- Кружок с буквой дня -->
        <!-- <div
          class="w-8 h-8 rounded-full bg-primary-500 text-white flex items-center justify-center font-semibold text-sm flex-shrink-0"
        >

        </div> -->
        <UBadge class="w-8 h-8 rounded-full flex items-center justify-center font-semibold text-sm">
          {{ day.letter }}
        </UBadge>
        <!-- Если день выключен -->
        <template v-if="!day.enabled">
          <span class="text-gray-500">Выкл.</span>
          <UButton
            icon="i-heroicons-plus"
            size="xs"
            color="neutral"
            variant="ghost"
            @click="enableDay(dayIndex)" />
        </template>
        <!-- Если день включен -->
        <template v-else-if="day.intervals[0]">
          <div class="flex flex-col">
            <div class="flex items-center gap-2">
              <!-- Поле начала интервала -->
              <TimeInput v-model="day.intervals[0].start" @change="save" />
              <!-- Тире -->
              <span class="text-gray-400">—</span>
              <!-- Поле окончания интервала -->
              <TimeInput v-model="day.intervals[0].end" @change="save" />
              <!-- Кнопка удалить -->
              <UButton
                icon="i-heroicons-x-mark"
                size="xs"
                color="neutral"
                variant="ghost"
                @click="disableDay(dayIndex)" />
              <!-- Кнопка добавить интервал -->
              <UButton
                icon="i-heroicons-plus"
                size="xs"
                color="neutral"
                variant="ghost"
                @click="addInterval(dayIndex)" />
              <!-- Кнопка копировать -->
              <!--<UPopover v-model:open="day.copyPopoverOpen">
                <UButton
                  icon="i-heroicons-document-duplicate"
                  size="xs"
                  color="neutral"
                  variant="ghost"
                />

                <template #content>
                  <div class="p-4 space-y-2">
                    <p class="text-sm font-semibold mb-3">Копировать в:</p>
                    <div class="space-y-2">
                      <UCheckbox
                        v-for="(targetDay, targetIndex) in schedule"
                        :key="targetIndex"
                        v-model="day.copyTargets[targetIndex]"
                        :label="getDayFullName(targetIndex)"
                        :disabled="targetIndex === dayIndex"
                      />
                    </div>
                    <div class="flex gap-2 mt-4">
                      <UButton size="xs" @click="copyIntervals(dayIndex)">Применить</UButton>
                      <UButton
                        size="xs"
                        color="neutral"
                        variant="ghost"
                        @click="day.copyPopoverOpen = false"
                      >
                        Отмена
                      </UButton>
                    </div>
                  </div>
                </template>
</UPopover> -->
            </div>
            <!-- Ошибка под интервалом -->
            <span v-if="day.intervals[0].error" class="text-xs text-red-500 mt-1">
              {{ day.intervals[0].error }}
            </span>
          </div>
        </template>
      </div>
      <!-- Дополнительные интервалы -->
      <div v-for="(interval, intervalIndex) in day.intervals.slice(1)" :key="intervalIndex" class="flex items-center gap-3 ml-11">
        <div class="flex flex-col">
          <div class="flex items-center gap-2">
            <!-- Поле начала интервала -->
            <TimeInput v-model="interval.start" @change="save" @blur="save" />
            <!-- Тире -->
            <span class="text-gray-400">—</span>
            <!-- Поле окончания интервала -->
            <TimeInput v-model="interval.end" @change="save" @blur="save" />
            <!-- Кнопка удалить -->
            <UButton icon="i-heroicons-x-mark" size="xs" color="neutral" variant="ghost" @click="removeInterval(dayIndex, intervalIndex + 1)" />
          </div>
          <span v-if="interval.error" class="text-xs text-red-500 mt-1">
            {{ interval.error }}
          </span>
        </div>
      </div>
    </div>
    <div class="text-sm mt-8">Исключаемые дни</div>
    <div class="grid grid-cols-7 gap-2">
      <UButton v-for="n in 31" :key="n" :label="String(n)" square class="w-full justify-center" :variant="isDayDisabled(n) ? 'ghost' : 'soft'" :color="isDayDisabled(n) ? 'neutral' : 'primary'" @click="toggleDay(n)" />
    </div>
  </div>
  <UModal v-model:open="createModalOpen" title="Новый календарь" description="Создание нового расписания">
    <template #body>
      <UFormField label="Название">
        <UInput v-model="newCalendarName" class="w-full" placeholder="Например: Консультант 2" />
      </UFormField>
    </template>
    <template #footer>
      <div class="flex justify-end gap-2">
        <UButton variant="ghost" color="neutral" @click="createModalOpen = false">Отмена</UButton>
        <UButton color="primary" :disabled="!newCalendarName.trim()" @click="handleCreateCalendar"> Создать </UButton>
      </div>
    </template>
  </UModal>
  <ConfirmModal v-model="deleteModalOpen" title="Удалить календарь" :description="`Удалить календарь '${selectedCalendarName}'?`" @confirm="handleDeleteCalendar" />
</template>
<script setup lang="ts">
import TimeInput from '@/components/dashboard/calendar/time-input.vue'
import ConfirmModal from '@/components/shared/confirm-modal.vue'
import { useSchedule } from '@/composables/use-schedule'
import { useTimezones } from '@/composables/use-timezones'
import { computed, onMounted, ref, watch } from 'vue'

const { timezones } = useTimezones()
const {
  load,
  loadCalendars,
  save,
  schedule,
  calendars,
  selectedScheduleId,
  timezone,
  meetingDuration,
  disabledMonthDays,
  toggleMonthDay,
  enableDay,
  disableDay,
  addInterval,
  removeInterval,
  createCalendar,
  updateCalendar,
  deleteCalendar,
  selectCalendar,
  /*  copyIntervals,

  getDayFullName, */
} = useSchedule()
const isHydrating = ref(false)
const createModalOpen = ref(false)
const deleteModalOpen = ref(false)
const newCalendarName = ref('')
const selectedCalendarId = ref<number>()

const calendarItems = computed(() =>
  calendars.value.map((calendar) => ({
    label: calendar.name,
    value: calendar.id,
  })),
)

const selectedCalendarName = computed(() => {
  return calendars.value.find((item) => item.id === selectedCalendarId.value)?.name ?? ''
})

const isDayDisabled = (day: number) => {
  return disabledMonthDays.value.includes(day)
}

const selectedTimezone = ref<string>()
const selectedMeetingDuration = ref<number>()

onMounted(async () => {
  isHydrating.value = true
  await loadCalendars()
  await load()
  selectedCalendarId.value = selectedScheduleId.value
  selectedTimezone.value = timezone.value
  selectedMeetingDuration.value = meetingDuration.value
  isHydrating.value = false
})

watch(selectedTimezone, async (val, oldVal) => {
  if (!val || val === oldVal || isHydrating.value) return
  await updateCalendar({ timezone: val })
})

watch(selectedMeetingDuration, async (val, oldVal) => {
  if (!val || val === oldVal || isHydrating.value) return
  await updateCalendar({ meetingDuration: val })
})

watch(selectedCalendarId, async (val, oldVal) => {
  if (!val || val === oldVal) return
  isHydrating.value = true
  await selectCalendar(val)
  selectedTimezone.value = timezone.value
  selectedMeetingDuration.value = meetingDuration.value
  isHydrating.value = false
})

const toggleDay = async (day: number) => {
  await toggleMonthDay({ day })

  // optimistic update
  if (isDayDisabled(day)) {
    disabledMonthDays.value = disabledMonthDays.value.filter((d) => d !== day)
  } else {
    disabledMonthDays.value.push(day)
  }
}

const handleCreateCalendar = async () => {
  const name = newCalendarName.value.trim()
  if (!name) return

  await createCalendar({
    name,
    timezone: selectedTimezone.value || 'Europe/Moscow',
    meetingDuration: selectedMeetingDuration.value || 30,
  })

  selectedCalendarId.value = selectedScheduleId.value
  selectedTimezone.value = timezone.value
  selectedMeetingDuration.value = meetingDuration.value
  newCalendarName.value = ''
  createModalOpen.value = false
}

const handleDeleteCalendar = async () => {
  if (!selectedCalendarId.value || calendarItems.value.length <= 1) return

  await deleteCalendar(selectedCalendarId.value)
  selectedCalendarId.value = selectedScheduleId.value
  selectedTimezone.value = timezone.value
  selectedMeetingDuration.value = meetingDuration.value
}
</script>
