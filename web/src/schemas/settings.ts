import * as v from 'valibot'

export const aiModelSchema = v.object({
  id: v.pipe(v.string(), v.minLength(1, 'API ключ обязателен')),
})

export type AiModelSchema = v.InferOutput<typeof aiModelSchema>

export const mobProxyFormSchema = v.object({
  host: v.pipe(v.string(), v.minLength(1, 'Хост обязателен')),
  port: v.pipe(v.number(), v.minValue(1, 'Порт должен быть больше 0')),
  username: v.pipe(v.string(), v.minLength(1, 'Логин обязателен')),
  password: v.pipe(v.string(), v.minLength(1, 'Пароль обязателен')),
  changeUrl: v.pipe(v.string(), v.url('Введите корректный URL')),
  country: v.pipe(v.string(), v.length(2, 'Код страны должен состоять из 2 символов')),
  active: v.boolean(),
})

export type MobProxyFormSchema = v.InferOutput<typeof mobProxyFormSchema>
