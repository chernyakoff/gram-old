import * as v from 'valibot'
import * as telegram from '@/schemas/atoms/telegram'

// ============================================
// Схемы валидации
// ============================================

export const accountSchema = v.objectAsync({
  username: v.nullable(telegram.username()),
  channel: v.nullable(telegram.username()),
  about: v.nullable(
    v.pipe(
      v.string('должно быть строкой'),
      v.maxLength(140, 'должно содержать не более 64 символов'),
    ),
  ),
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
})

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
