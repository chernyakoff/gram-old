import * as v from 'valibot'

export const proxyApiSchema = v.object({
  apiKey: v.pipe(
    v.string(),
    v.minLength(1, 'API ключ обязателен'),
    v.regex(
      /^sk-[A-Za-z0-9]+$/,
      'API ключ должен начинаться с "sk-" и содержать только латинские буквы и цифры',
    ),
    v.minLength(10, 'API ключ слишком короткий'), // можете настроить минимальную длину
  ),
})

export const settingsSchema = v.object({
  proxyApi: proxyApiSchema,
})

export type SettingsSchema = v.InferOutput<typeof settingsSchema>
