import * as v from 'valibot'

export const aiModelSchema = v.object({
  id: v.pipe(v.string(), v.minLength(1, 'API ключ обязателен')),
})

export type AiModelSchema = v.InferOutput<typeof aiModelSchema>
