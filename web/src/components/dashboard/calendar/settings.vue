<template>
  <div class="mx-auto w-max space-y-4 px-4">
    <div v-for="(day, dayIndex) in schedule" :key="dayIndex" class="space-y-1">
      <!-- Основная строка дня -->
      <div class="flex items-center gap-3">
        <!-- Кружок с буквой дня -->
        <div
          class="w-8 h-8 rounded-full bg-primary-500 text-white flex items-center justify-center font-semibold text-sm flex-shrink-0"
        >
          {{ day.letter }}
        </div>

        <!-- Если день выключен -->
        <template v-if="!day.enabled">
          <span class="text-gray-500">Выкл.</span>
          <UButton
            icon="i-heroicons-plus"
            size="xs"
            color="neutral"
            variant="ghost"
            @click="enableDay(dayIndex)"
          />
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
                @click="disableDay(dayIndex)"
              />

              <!-- Кнопка добавить интервал -->
              <UButton
                icon="i-heroicons-plus"
                size="xs"
                color="neutral"
                variant="ghost"
                @click="addInterval(dayIndex)"
              />

              <!-- Кнопка копировать -->
              <UPopover v-model:open="day.copyPopoverOpen">
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
              </UPopover>
            </div>

            <!-- Ошибка под интервалом -->
            <span v-if="day.intervals[0].error" class="text-xs text-red-500 mt-1">
              {{ day.intervals[0].error }}
            </span>
          </div>
        </template>
      </div>

      <!-- Дополнительные интервалы -->
      <div
        v-for="(interval, intervalIndex) in day.intervals.slice(1)"
        :key="intervalIndex"
        class="flex items-center gap-3 ml-11"
      >
        <div class="flex flex-col">
          <div class="flex items-center gap-2">
            <!-- Поле начала интервала -->
            <TimeInput v-model="interval.start" @change="save" @blur="save" />

            <!-- Тире -->
            <span class="text-gray-400">—</span>

            <!-- Поле окончания интервала -->
            <TimeInput v-model="interval.end" @change="save" @blur="save" />

            <!-- Кнопка удалить -->
            <UButton
              icon="i-heroicons-x-mark"
              size="xs"
              color="neutral"
              variant="ghost"
              @click="removeInterval(dayIndex, intervalIndex + 1)"
            />
          </div>

          <span v-if="interval.error" class="text-xs text-red-500 mt-1">
            {{ interval.error }}
          </span>
        </div>
      </div>
    </div>
    <USelectMenu
      class="w-full mt-4"
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
      placeholder="Выберите таймзону"
    />
  </div>
</template>

<script setup lang="ts">
import TimeInput from '@/components/dashboard/calendar/time-input.vue'
import { useSchedule } from '@/composables/use-schedule'
import { useTimezones } from '@/composables/use-timezones'
import { onMounted, ref } from 'vue'

const { timezones, loadTimezone } = useTimezones()
const {
  load,
  save,
  schedule,
  enableDay,
  disableDay,
  addInterval,
  removeInterval,
  copyIntervals,

  getDayFullName,
} = useSchedule()
// Инициализация расписания

const selectedTimezone = ref('Europe/Moscow')

// Загрузка данных при монтировании (опционально)
onMounted(async () => {
  await load()
  selectedTimezone.value = await loadTimezone()
})
</script>
