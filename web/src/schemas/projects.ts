import * as v from 'valibot'

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

const optionalTextSchema = v.optional(v.string(), '')

const hourSchema = v.pipe(v.number('обязательное поле'), v.minValue(0), v.maxValue(24))

// Схемы с опциональными полями
export const briefInSchema = v.object({
  description: optionalTextSchema,
  client: optionalTextSchema,
  offer: optionalTextSchema,
  pains: optionalTextSchema,
  advantages: optionalTextSchema,
  mission: optionalTextSchema,
  focus: optionalTextSchema,
})

export type BriefInSchema = v.InferOutput<typeof briefInSchema>

export const promptInSchema = v.object({
  role: optionalTextSchema,
  context: optionalTextSchema,
  init: optionalTextSchema,
  engage: optionalTextSchema,
  offer: optionalTextSchema,
  closing: optionalTextSchema,
  instruction: optionalTextSchema,
  rules: optionalTextSchema,
})

const skipOptionsSchema = v.object({
  engage: v.boolean(),
  offer: v.boolean(),
  closing: v.boolean(),
})

export type PromptInSchema = v.InferOutput<typeof promptInSchema>

// Базовая схема
const baseProjectSchema = v.object({
  name: v.pipe(
    v.string(),
    v.nonEmpty('обязательное поле'),
    v.maxLength(64, 'должно содержать не более 64 символов'),
  ),
  dialogLimit: limitShema,
  sendTimeStart: hourSchema,
  sendTimeEnd: hourSchema,
  firstMessage: textSchema,
  advancedMode: v.boolean(),
  brief: briefInSchema,
  prompt: promptInSchema,
  skipOptions: skipOptionsSchema,
})

type BaseProjectSchemaType = v.InferOutput<typeof baseProjectSchema>

// Валидация полей brief
const validateBriefField = (fieldName: keyof BriefInSchema) =>
  v.forward(
    v.check((data: BaseProjectSchemaType) => {
      if (data.advancedMode) return true
      const value = data.brief[fieldName]
      return typeof value === 'string' && value.trim().length >= 32
    }, 'обязательное поле (минимум 32 символа)'),
    ['brief', fieldName],
  )

// Валидация полей prompt
const validatePromptField = (fieldName: keyof PromptInSchema) =>
  v.forward(
    v.check((data: BaseProjectSchemaType) => {
      if (!data.advancedMode) return true
      const value = data.prompt[fieldName]
      return typeof value === 'string' && value.trim().length >= 32
    }, 'обязательное поле (минимум 32 символа)'),
    ['prompt', fieldName],
  )

// Применяем все валидации
export const projectInSchema = v.pipe(
  baseProjectSchema,
  // Валидация brief полей
  validateBriefField('description'),
  validateBriefField('client'),
  validateBriefField('offer'),
  validateBriefField('pains'),
  validateBriefField('advantages'),
  validateBriefField('mission'),
  validateBriefField('focus'),
  // Валидация prompt полей
  validatePromptField('role'),
  validatePromptField('context'),
  validatePromptField('init'),
  validatePromptField('engage'),
  validatePromptField('offer'),
  validatePromptField('closing'),
  validatePromptField('instruction'),
  validatePromptField('rules'),
)

export type ProjectInSchema = v.InferOutput<typeof projectInSchema>
