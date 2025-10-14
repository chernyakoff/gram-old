import * as v from 'valibot'

import type { ProjectIn } from '@/types/openapi'

const limitShema = v.pipe(
  v.number(),
  v.minValue(1, 'должно быть больше 1'),
  v.maxValue(100, 'должно быть не больше 100'),
)

const textSchema = v.pipe(
  v.string('должно быть строкой'),
  v.nonEmpty('обязательное поле'),
  v.minLength(32, 'должно содержать хотя бы 32 символа'),
)

const hourSchema = v.pipe(v.number('обязательное поле'), v.minValue(0), v.maxValue(24))

export const projectInSchema = v.object({
  name: v.pipe(
    v.string(),
    v.nonEmpty('обязательное поле'),
    v.maxLength(64, 'должно содержать не более 64 символов'),
  ),
  dialogLimit: limitShema,
  outDailyLimit: limitShema,
  sendTimeStart: hourSchema,
  sendTimeEnd: hourSchema,
  firstMessage: textSchema,
  prompt: textSchema,
}) as v.GenericSchema<ProjectIn>

export type ProjectInSchema = v.InferOutput<typeof projectInSchema>
