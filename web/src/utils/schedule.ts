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
export const TIME_STEP = 15

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
