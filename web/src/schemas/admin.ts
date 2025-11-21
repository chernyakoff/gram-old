import * as v from 'valibot'
import * as telegram from '@/schemas/atoms/telegram'

// ============================================
// Схемы валидации
// ============================================

const daysSchema = v.pipe(v.number(), v.minValue(1, 'должно быть больше 1'))

export const licenseSchema = v.object({
  username: telegram.username(),
  days: daysSchema,
})

export type LicenseSchema = v.InferOutput<typeof licenseSchema>
