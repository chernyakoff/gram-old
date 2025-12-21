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

export const balanceSchema = v.object({
  username: telegram.username(),
  amount: daysSchema,
})

export const impersonateSchema = v.object({
  username: telegram.username(),
})

const textSchema = v.pipe(
  v.string('должно быть строкой'),
  v.nonEmpty('обязательное поле'),
  v.minLength(32, 'должно содержать хотя бы 32 символа'),
)

export const appSettingSchema = v.object({
  path: v.string(),
  value: textSchema,
})

export type AppSettingSchema = v.InferOutput<typeof appSettingSchema>

export type LicenseSchema = v.InferOutput<typeof licenseSchema>

export type BalanceSchema = v.InferOutput<typeof balanceSchema>

export type ImpersonateSchema = v.InferOutput<typeof impersonateSchema>
