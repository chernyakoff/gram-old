import * as v from 'valibot'
import * as telegram from '@/schemas/atoms/telegram'

// ============================================
// Схемы валидации
// ============================================

// Динамическая валидация about в зависимости от premium
export const accountSchema = v.pipe(
  v.object({
    username: v.nullable(telegram.username()),
    channel: v.nullable(telegram.username()),
    premium: v.boolean(),
    about: v.nullable(v.string('должно быть строкой')),

    firstName: v.nullable(
      v.pipe(
        v.string('должно быть строкой'),
        v.maxLength(32, 'должно содержать не более 32 символов'),
      ),
    ),
    lastName: v.nullable(
      v.pipe(
        v.string('должно быть строкой'),
        v.maxLength(32, 'должно содержать не более 32 символов'),
      ),
    ),
  }),
  v.forward(
    v.partialCheck(
      [['about'], ['premium']],
      (input) => {
        if (!input.about) return true
        const maxLength = input.premium ? 140 : 70
        return input.about?.length <= maxLength
      },
      'Превышена допустимая длина',
    ),
    ['about'],
  ),
)

export type AccountSchema = v.InferOutput<typeof accountSchema>

export interface EditableAccountPhoto {
  id: number
  url: string
  file?: File
  markedForDeletion?: boolean
}

export interface AccountPhotosChanges {
  toDelete: number[]
  toUpload: File[]
  hasChanges: boolean
}

export interface AccountUpdatePayload extends AccountSchema {
  photos: {
    upload: string[]
    delete: number[]
  }
}
