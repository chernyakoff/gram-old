import * as v from 'valibot'

const MAX_BYTES = 1024 * 1024 // 1 MB

// Схема для одного файла
const textFileSchema = v.pipe(
  v.file('Выберите файл'),
  v.mimeType(['text/plain'], 'Выберите TXT'),
  v.maxSize(MAX_BYTES, 'Файл ≤ 1MB'),
)

// Схема для массива файлов
export const textFilesArraySchema = v.object({
  files: v.pipe(
    v.array(textFileSchema, 'Файлы должны быть массивом'),
    v.minLength(1, 'Выберите хотя бы один файл'), // опционально
    v.maxLength(10, 'Максимум 10 файлов'), // опционально
  ),
})

export type TextFilesArraySchema = v.InferOutput<typeof textFilesArraySchema>
