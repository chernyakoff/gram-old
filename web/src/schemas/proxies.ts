import * as v from 'valibot'

const MAX_BYTES = 1024 * 1024 // 1 MB

const baseSchema = v.object({
  file: v.optional(
    v.pipe(
      v.file('Выберите файл'),
      v.mimeType(['text/plain'], 'Выберите TXT'),
      v.maxSize(MAX_BYTES, 'Файл ≤ 1MB'),
    ),
  ),
  text: v.optional(
    v.pipe(
      v.string('Укажите текст'),
      v.nonEmpty('Текст не пустой'),
      v.check((t) => new TextEncoder().encode(t).length <= MAX_BYTES, 'Текст ≤ 1MB'),
    ),
  ),
})

type BaseSchemaType = v.InferOutput<typeof baseSchema>

export const proixiesBulkCreateForm = v.pipe(
  baseSchema,
  v.forward(
    v.check((data: BaseSchemaType) => {
      const hasFile = data.file instanceof File
      const hasText = Boolean(data.text && data.text.trim().length > 0) // Явное приведение к boolean
      return hasFile || hasText
    }, 'Выберите файл или введите текст'),
    ['text'],
  ),

  v.forward(
    v.check((data: BaseSchemaType) => {
      const hasFile = data.file instanceof File
      const hasText = Boolean(data.text && data.text.trim().length > 0) // Явное приведение к boolean
      return hasFile || hasText
    }, 'Выберите файл или введите текст'),
    ['file'],
  ),
)

export type ProixiesBulkCreateForm = v.InferOutput<typeof proixiesBulkCreateForm>

export const proixiesBulkCreateSchema = v.pipeAsync(
  proixiesBulkCreateForm,
  v.transformAsync(async ({ file, text }) => {
    let content = text ?? ''
    if (file) {
      content = await file.text()
    }
    const proxies = content
      .split(/[\n,;]+/)
      .map((s) => s.trim())
      .filter(Boolean)

    if (proxies.length === 0) {
      throw new Error('Нужно указать хотя бы одного пользователя')
    }

    return { proxies }
  }),
)
