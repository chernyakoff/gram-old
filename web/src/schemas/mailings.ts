import * as v from 'valibot'

const MAX_BYTES = 1024 * 1024 // 1 MB

const baseSchema = v.object({
  name: v.pipe(
    v.string(),
    v.nonEmpty('обязательное поле'),
    v.maxLength(64, 'должно содержать не более 64 символов'),
  ),
  projectId: v.pipe(
    v.optional(v.number(), undefined),
    v.check((val) => val !== undefined, 'Нужно выбрать проект'),
  ),
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

export const mailingFormSchema = v.pipe(
  baseSchema,
  v.forward(
    v.check((data: BaseSchemaType) => {
      const hasFile = data.file instanceof File
      const hasText = Boolean(data.text && data.text.trim().length > 0) // Явное приведение к boolean
      return hasFile || hasText
    }, 'Выберите файл или введите текст'),
    ['text'],
  ),
  // Ошибка для поля file
  v.forward(
    v.check((data: BaseSchemaType) => {
      const hasFile = data.file instanceof File
      const hasText = Boolean(data.text && data.text.trim().length > 0) // Явное приведение к boolean
      return hasFile || hasText
    }, 'Выберите файл или введите текст'),
    ['file'],
  ),
)

export type MailingFormSchema = v.InferOutput<typeof mailingFormSchema>

export const mailingInSchema = v.pipeAsync(
  mailingFormSchema,
  v.transformAsync(async ({ projectId, file, text, name }) => {
    if (!projectId || projectId <= 0) {
      throw new Error('Нужно выбрать проект')
    }
    let content = text ?? ''
    if (file) {
      content = await file.text()
    }
    const recipients = content
      .split(/[\n,;]+/)
      .map((s) => s.trim())
      .filter(Boolean)

    if (recipients.length === 0) {
      throw new Error('Нужно указать хотя бы одного пользователя')
    }

    return {
      name,
      projectId,
      recipients,
    }
  }),
)

export type MailingInSchema = v.InferOutput<typeof mailingInSchema>
