// statusConfig.ts

const STATUS_KEYS = [
  'init',
  'engage',
  'offer',
  'closing',
  'complete',
  'negative',
  'operator',
  'manual',
] as const

const STATUS_CONFIG = {
  init: { label: 'начат', color: '#006a6c' }, // темно-бирюзовый — начальный статус, нейтральный
  engage: { label: 'интерес', color: '#8e90ff' }, // светло-синий — общение с юзером активно
  offer: { label: 'диалог', color: '#ffab00' }, // оранжевый — предложение/коммерческий интерес
  closing: { label: 'закрытие', color: '#71dd37' }, // зеленый — этап заключения сделки
  complete: { label: 'заявка', color: '#ff5733' }, // красно-оранжевый — завершено, финальный статус
  negative: { label: 'негатив', color: '#d32f2f' }, // ярко-красный — юзер недоволен общением
  operator: { label: 'оператор', color: '#6a1b9a' }, // фиолетовый — юзер хочет живого человека, вмешательство оператора
  manual: { label: 'ручной', color: '#455a64' }, // графитово-синий — диалог ведёт менеджер вручную
} as const

// Добавляем short автоматически
const STATUS_CONFIG_WITH_SHORT = Object.fromEntries(
  STATUS_KEYS.map((key, idx) => [
    key,
    { ...STATUS_CONFIG[key], short: (STATUS_KEYS.length - idx).toString() },
  ]),
) as typeof STATUS_CONFIG & Record<(typeof STATUS_KEYS)[number], { short: string }>

// Производные структуры
export const statusColor = Object.fromEntries(
  STATUS_KEYS.map((key) => [key, STATUS_CONFIG_WITH_SHORT[key].color]),
) as Record<(typeof STATUS_KEYS)[number], string>

export const colors = STATUS_KEYS.map((key) => STATUS_CONFIG_WITH_SHORT[key].color)

export const labelsMap = Object.fromEntries(
  STATUS_KEYS.map((key) => [key, STATUS_CONFIG_WITH_SHORT[key].label]),
) as Record<(typeof STATUS_KEYS)[number], string>

export const categories = STATUS_KEYS.map((key) => STATUS_CONFIG_WITH_SHORT[key].label)

export const shortLabels = STATUS_KEYS.map((key) => STATUS_CONFIG_WITH_SHORT[key].short)

// Массив для селекта
export const statuses = [
  { label: 'все', value: 'all' },
  ...STATUS_KEYS.map((key) => ({
    label: STATUS_CONFIG_WITH_SHORT[key].label,
    value: key,
  })),
]
