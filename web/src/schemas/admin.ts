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

export const impersonateSchema = v.object({
  username: telegram.username(),
})

export type LicenseSchema = v.InferOutput<typeof licenseSchema>

export type ImpersonateSchema = v.InferOutput<typeof impersonateSchema>
