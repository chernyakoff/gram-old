import {
  DEFAULT_SCHEDULE,
  formatMinutesToTime,
  parseTimeToMinutes,
  validateDayIntervals,
  type DaySchedule,
} from '@/utils/schedule'
import { ref } from 'vue'

export const useSchedule = () => {
  const schedule = ref<DaySchedule[]>(structuredClone(DEFAULT_SCHEDULE))

  const enableDay = (index: number) => {
    const day = schedule.value[index]
    if (!day) return

    day.enabled = true
    if (day.intervals.length === 0) {
      day.intervals.push({ start: '09:00', end: '18:00' })
    }
  }

  const disableDay = (index: number) => {
    const day = schedule.value[index]
    if (!day) return
    day.enabled = false
  }

  function addInterval(index: number) {
    const day = schedule.value[index]
    if (!day || !day.enabled) return
    if (!day.intervals[0]) {
      // Если интервала нет — просто создаём стандартный
      day.intervals.push({ start: '09:00', end: '10:00' })
      return
    }

    const first = day.intervals[0]
    const firstEnd = parseTimeToMinutes(first.end)
    const newStart = firstEnd + 60 // через 1 час после окончания первого интервала
    const newEnd = newStart + 60 // длина нового интервала = 60 мин

    // Если новый интервал не пересекается с первым
    if (newStart >= parseTimeToMinutes(first.start) && newStart < 24 * 60) {
      day.intervals.push({
        start: formatMinutesToTime(newStart),
        end: formatMinutesToTime(newEnd),
      })
    } else {
      // иначе уменьшаем первый интервал на 2 часа и добавляем новый в конец
      const reducedEnd = parseTimeToMinutes(first.end) - 120
      if (reducedEnd > parseTimeToMinutes(first.start)) {
        first.end = formatMinutesToTime(reducedEnd)
      }
      day.intervals.push({
        start: formatMinutesToTime(reducedEnd),
        end: formatMinutesToTime(reducedEnd + 60),
      })
    }
  }

  const removeInterval = (dayIndex: number, intervalIndex: number) => {
    schedule.value[dayIndex]?.intervals.splice(intervalIndex, 1)
  }

  const copyIntervals = (from: number) => {
    const source = schedule.value[from]
    if (!source) return

    source.copyTargets.forEach((copy, to) => {
      if (copy && to !== from) {
        const target = schedule.value[to]
        if (!target) return

        target.enabled = source.enabled
        target.intervals = structuredClone(source.intervals)
      }
    })

    source.copyTargets = source.copyTargets.map(() => false)
    source.copyPopoverOpen = false
  }

  const validateAll = (): boolean => {
    return schedule.value.every(validateDayIntervals)
  }

  const getDayFullName = (dayIndex: number): string => {
    return schedule.value[dayIndex]?.name || ''
  }

  return {
    schedule,
    enableDay,
    getDayFullName,
    disableDay,
    addInterval,
    removeInterval,
    copyIntervals,
    validateAll,
  }
}
