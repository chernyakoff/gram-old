<template>
  <div class="space-y-2">
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
              <TimeInput
                v-model="day.intervals[0].start"
                @change="saveToServer"
                @blur="saveToServer"
              />

              <!-- Тире -->
              <span class="text-gray-400">—</span>

              <!-- Поле окончания интервала -->
              <TimeInput
                v-model="day.intervals[0].end"
                @change="saveToServer"
                @blur="saveToServer"
              />

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
                @click="handleAddInterval(dayIndex)"
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
                      <UButton size="xs" @click="handleCopyIntervals(dayIndex)">Применить</UButton>
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
            <TimeInput v-model="interval.start" @change="saveToServer" @blur="saveToServer" />

            <!-- Тире -->
            <span class="text-gray-400">—</span>

            <!-- Поле окончания интервала -->
            <TimeInput v-model="interval.end" @change="saveToServer" @blur="saveToServer" />

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
  </div>
</template>

<script setup lang="ts">
import TimeInput from '@/components/dashboard/calendar/time-input.vue'
import { useSchedule } from '@/composables/use-schedule'

const {
  schedule,
  enableDay,
  disableDay,
  addInterval,
  removeInterval,
  copyIntervals,
  validateAll,
  getDayFullName,
} = useSchedule()
// Инициализация расписания

const handleCopyIntervals = async (dayIndex: number) => {
  copyIntervals(dayIndex)
  await saveToServer()
}

const handleAddInterval = (dayIndex: number) => {
  addInterval(dayIndex)
  saveToServer()
}

// Сохранение на сервер
const saveToServer = async () => {
  if (!validateAll()) {
    console.log('POP')
    return
  }
  try {
    // Пример API запроса
    const response = '' /* await $fetch('/api/working-hours', {
      method: 'POST',
      body: {
        schedule: schedule.value.map((day) => ({
          name: day.name,
          enabled: day.enabled,
          intervals: day.intervals,
        })),
      },
    }) */

    console.log('Расписание сохранено:', response)
  } catch (error) {
    console.error('Ошибка сохранения:', error)
  }
}

// Загрузка данных при монтировании (опционально)
// onMounted(async () => {
//   try {
//     const data = await $fetch('/api/working-hours')
//     if (data?.schedule) {
//       schedule.value = data.schedule
//     }
//   } catch (error) {
//     console.error('Ошибка загрузки:', error)
//   }
// })
</script>
