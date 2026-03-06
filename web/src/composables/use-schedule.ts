import type {
  ScheduleCreateIn,
  ScheduleIn,
  ScheduleMetaOut,
  ScheduleOut,
  ScheduleUpdateIn,
  ToggleDayIn,
} from '@/types/openapi'
import { ref } from 'vue'
import { useApi } from './use-api'
/*
(alias) type ScheduleIn = {
    schedule: {
        weekday: number;
        enabled: boolean;
        intervals: {
            start: string;
            end: string;
        }[];
    }[];
}
type ScheduleOut = {
    schedule: {
        weekday: number;
        enabled: boolean;
        intervals: {
            start: string;
            end: string;
        }[];
    }[];
    timezone: string;
    disabledMonthDays: number[];
    meetingDuration: number;
}
 type ToggleDayIn = {
    day: number;
}


*/
export interface Interval {
  start: string
  end: string
  error?: string
}

export interface DaySchedule {
  letter: string
  name: string
  enabled: boolean
  intervals: Interval[]
  copyPopoverOpen: boolean
  copyTargets: boolean[]
}
export const TIME_STEP = 60

export const DEFAULT_INTERVAL = {
  start: '09:00',
  end: '18:00',
}

export const DEFAULT_SCHEDULE: DaySchedule[] = [
  {
    letter: 'П',
    name: 'Понедельник',
    enabled: true,
    intervals: [{ ...DEFAULT_INTERVAL }],
    copyPopoverOpen: false,
    copyTargets: Array(7).fill(false),
  },
  {
    letter: 'В',
    name: 'Вторник',
    enabled: true,
    intervals: [{ ...DEFAULT_INTERVAL }],
    copyPopoverOpen: false,
    copyTargets: Array(7).fill(false),
  },
  {
    letter: 'С',
    name: 'Среда',
    enabled: true,
    intervals: [{ ...DEFAULT_INTERVAL }],
    copyPopoverOpen: false,
    copyTargets: Array(7).fill(false),
  },
  {
    letter: 'Ч',
    name: 'Четверг',
    enabled: true,
    intervals: [{ ...DEFAULT_INTERVAL }],
    copyPopoverOpen: false,
    copyTargets: Array(7).fill(false),
  },
  {
    letter: 'П',
    name: 'Пятница',
    enabled: true,
    intervals: [{ ...DEFAULT_INTERVAL }],
    copyPopoverOpen: false,
    copyTargets: Array(7).fill(false),
  },
  {
    letter: 'С',
    name: 'Суббота',
    enabled: false,
    intervals: [{ ...DEFAULT_INTERVAL }],
    copyPopoverOpen: false,
    copyTargets: Array(7).fill(false),
  },
  {
    letter: 'В',
    name: 'Воскресенье',
    enabled: false,
    intervals: [{ ...DEFAULT_INTERVAL }],
    copyPopoverOpen: false,
    copyTargets: Array(7).fill(false),
  },
]

const WEEKDAYS = [
  { number: 1, letter: 'П', name: 'Понедельник' },
  { number: 2, letter: 'В', name: 'Вторник' },
  { number: 3, letter: 'С', name: 'Среда' },
  { number: 4, letter: 'Ч', name: 'Четверг' },
  { number: 5, letter: 'П', name: 'Пятница' },
  { number: 6, letter: 'С', name: 'Суббота' },
  { number: 7, letter: 'В', name: 'Воскресенье' },
]

// Получить букву дня по числу
export const getWeekdayLetter = (weekdayNumber: number): string => {
  return WEEKDAYS.find((d) => d.number === weekdayNumber)?.letter ?? '?'
}

// Получить полное название дня по числу
export const getWeekdayName = (weekdayNumber: number): string => {
  return WEEKDAYS.find((d) => d.number === weekdayNumber)?.name ?? 'Неизвестно'
}

// Получить число дня по букве (для toApi)
export const getWeekdayNumber = (name: string): number => {
  return WEEKDAYS.find((d) => d.name === name)?.number ?? 0
}

export const parseTimeToMinutes = (time: string): number => {
  const parts = time.split(':')

  if (parts.length !== 2) return 0

  const h = Number(parts[0])
  const m = Number(parts[1])

  if (Number.isInteger(h) && Number.isInteger(m) && h >= 0 && h < 24 && m >= 0 && m < 60) {
    return h * 60 + m
  }

  return 0
}

export const validateInterval = (interval: Interval): boolean => {
  const start = parseTimeToMinutes(interval.start)
  const end = parseTimeToMinutes(interval.end)

  if (start === null || end === null) {
    interval.error = 'Неверный формат времени'
    return false
  }

  if (start >= end) {
    interval.error = 'Начало должно быть раньше окончания'
    return false
  }

  delete interval.error
  return true
}

export const validateDayIntervals = (day: DaySchedule): boolean => {
  if (!day.enabled) return true

  let valid = true

  for (const interval of day.intervals) {
    if (!validateInterval(interval)) valid = false
  }

  if (!valid) return false

  day.intervals.forEach((a, i) => {
    const startA = parseTimeToMinutes(a.start)
    const endA = parseTimeToMinutes(a.end)
    if (startA === null || endA === null) return

    day.intervals.slice(i + 1).forEach((b) => {
      const startB = parseTimeToMinutes(b.start)
      const endB = parseTimeToMinutes(b.end)
      if (startB === null || endB === null) return

      if (startA < endB && endA > startB) {
        a.error = 'Интервалы пересекаются'
        b.error = 'Интервалы пересекаются'
        valid = false
      }
    })
  })

  return valid
}

export function formatMinutesToTime(minutes: number) {
  const h = String(Math.floor(minutes / 60)).padStart(2, '0')
  const m = String(minutes % 60).padStart(2, '0')
  return `${h}:${m}`
}

export const useSchedule = () => {
  const schedule = ref<DaySchedule[]>(structuredClone(DEFAULT_SCHEDULE))
  const { api, loading, error, success } = useApi()
  const calendars = ref<ScheduleMetaOut[]>([])
  const selectedScheduleId = ref<number>()
  const currentScheduleName = ref<string>()
  const meetingDuration = ref<number>()
  const timezone = ref<string>()
  const disabledMonthDays = ref<number[]>([])

  const fromApi = (data: ScheduleOut) => {
    return data.schedule.map((day) => {
      const weekday = WEEKDAYS.find((d) => d.number === day.weekday)
      return {
        letter: weekday?.letter ?? '?',
        name: weekday?.name ?? '',
        enabled: day.enabled,
        intervals: day.intervals.map((i) => ({ start: i.start, end: i.end, error: '' })),
        copyPopoverOpen: false,
        copyTargets: Array(7).fill(false),
      }
    })
  }

  const toApi = () => {
    return {
      schedule: schedule.value.map((day) => ({
        weekday: getWeekdayNumber(day.name),
        enabled: day.enabled,
        intervals: day.intervals.map((i) => ({ start: i.start, end: i.end })),
      })),
    } as ScheduleIn
  }

  const withScheduleQuery = (path: string, scheduleId = selectedScheduleId.value) => {
    if (!scheduleId) return path
    const delimiter = path.includes('?') ? '&' : '?'
    return `${path}${delimiter}schedule_id=${scheduleId}`
  }

  async function loadCalendars() {
    const list = await api<ScheduleMetaOut[]>('schedule/list')
    calendars.value = list
    if (!selectedScheduleId.value && list.length > 0) {
      const defaultCalendar = list.find((item) => item.isDefault)
      selectedScheduleId.value = defaultCalendar?.id ?? list[0]?.id
    }
    return list
  }

  async function load(scheduleId?: number) {
    try {
      if (scheduleId) {
        selectedScheduleId.value = scheduleId
      }

      if (!calendars.value.length) {
        await loadCalendars()
      }

      const data = await api<ScheduleOut>(withScheduleQuery('schedule'))

      // Если data пустое или schedule отсутствует — берем DEFAULT_SCHEDULE
      if (!data || !Array.isArray(data.schedule) || data.schedule.length === 0) {
        schedule.value = structuredClone(DEFAULT_SCHEDULE)
        await save()
        return
      }
      selectedScheduleId.value = data.scheduleId
      currentScheduleName.value = data.name
      timezone.value = data.timezone
      meetingDuration.value = data.meetingDuration
      schedule.value = fromApi(data)
      disabledMonthDays.value = data.disabledMonthDays
    } catch (e) {
      console.error('Ошибка загрузки расписания', e)
      // Можно тоже вернуть DEFAULT_SCHEDULE на случай ошибки
      schedule.value = structuredClone(DEFAULT_SCHEDULE)
    }
  }

  async function save() {
    if (!validateAll()) return
    try {
      const payload = toApi()
      await api(withScheduleQuery('schedule/working-hours'), { method: 'POST', body: payload })
    } catch (e) {
      console.error('Ошибка сохранения', e)
    }
  }

  const enableDay = async (index: number) => {
    const day = schedule.value[index]
    if (!day) return

    day.enabled = true
    if (day.intervals.length === 0) {
      day.intervals.push({ start: '09:00', end: '18:00' })
    }
    await save()
  }

  const disableDay = async (index: number) => {
    const day = schedule.value[index]
    if (!day) return
    day.enabled = false
    day.intervals = [{ ...DEFAULT_INTERVAL }]
    await save()
  }

  async function addInterval(index: number) {
    const day = schedule.value[index]
    if (!day || !day.enabled) return

    if (day.intervals.length === 0) {
      day.intervals.push({ ...DEFAULT_INTERVAL })
      return
    }

    const last = day.intervals.at(-1)
    if (!last) return

    const lastEnd = parseTimeToMinutes(last.end)
    if (lastEnd === null) return

    const newStart = lastEnd + 60
    const newEnd = newStart + 60

    // ❌ запрещаем 24:00 и всё, что дальше
    if (newEnd >= 24 * 60) return

    day.intervals.push({
      start: formatMinutesToTime(newStart),
      end: formatMinutesToTime(newEnd),
    })

    await save()
  }

  const removeInterval = async (dayIndex: number, intervalIndex: number) => {
    schedule.value[dayIndex]?.intervals.splice(intervalIndex, 1)
    await save()
  }

  const copyIntervals = async (from: number) => {
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
    await save()
  }

  const validateAll = (): boolean => {
    return schedule.value.every(validateDayIntervals)
  }

  const getDayFullName = (dayIndex: number): string => {
    return schedule.value[dayIndex]?.name || ''
  }

  async function toggleMonthDay(body: ToggleDayIn): Promise<void> {
    return await api(withScheduleQuery('schedule/toggle-day'), { method: 'POST', body })
  }

  async function createCalendar(body: ScheduleCreateIn) {
    const created = await api<ScheduleMetaOut>('schedule', { method: 'POST', body })
    await loadCalendars()
    await load(created.id)
    return created
  }

  async function updateCalendar(body: ScheduleUpdateIn, scheduleId = selectedScheduleId.value) {
    if (!scheduleId) return

    const updated = await api<ScheduleMetaOut>(`schedule/${scheduleId}`, {
      method: 'PATCH',
      body,
    })

    await loadCalendars()
    const targetId = body.isDefault ? updated.id : selectedScheduleId.value
    await load(targetId)
    return updated
  }

  async function deleteCalendar(scheduleId: number) {
    await api<void>(`schedule/${scheduleId}`, { method: 'DELETE' })
    await loadCalendars()

    if (selectedScheduleId.value === scheduleId) {
      const nextId = calendars.value.find((item) => item.isDefault)?.id ?? calendars.value[0]?.id
      if (nextId) {
        await load(nextId)
      } else {
        selectedScheduleId.value = undefined
        currentScheduleName.value = undefined
        schedule.value = structuredClone(DEFAULT_SCHEDULE)
        disabledMonthDays.value = []
      }
    }
  }

  async function selectCalendar(scheduleId: number) {
    if (selectedScheduleId.value === scheduleId) return
    await load(scheduleId)
  }

  return {
    loading,
    error,
    success,
    load,
    save,
    loadCalendars,
    schedule,
    calendars,
    selectedScheduleId,
    currentScheduleName,
    timezone,
    meetingDuration,
    disabledMonthDays,
    enableDay,
    getDayFullName,
    disableDay,
    addInterval,
    removeInterval,
    copyIntervals,
    validateAll,
    toggleMonthDay,
    createCalendar,
    updateCalendar,
    deleteCalendar,
    selectCalendar,
  }
}
