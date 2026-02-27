import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { AccountOut } from '@/types/openapi'
import type { AccountSchema, AccountUpdatePayload } from '@/schemas/accounts'
import type { AccountPhotosChanges, EditableAccountPhoto } from '@/schemas/accounts'

export const useAccountEditor = defineStore('accountEditor', () => {
  const trimNullable = (value: string | null | undefined, maxLength: number): string | null => {
    if (value == null) return null
    return value.slice(0, maxLength)
  }

  const normalizeAccountProfile = (account: AccountOut): AccountSchema => {
    const aboutMaxLength = account.premium ? 140 : 70
    return {
      username: account.username ?? null,
      channel: account.channel ?? null,
      premium: account.premium,
      about: trimNullable(account.about, aboutMaxLength),
      firstName: trimNullable(account.firstName, 32),
      lastName: trimNullable(account.lastName, 32),
    }
  }

  // State
  const profile = ref<AccountSchema>({} as AccountSchema)
  const photos = ref<EditableAccountPhoto[]>([])
  const originalProfile = ref<AccountSchema | null>(null)
  const currentAccountId = ref<number | null>(null)
  const isSaving = ref(false)

  // Utils
  const parsePhotos = (photos: AccountOut['photos']): EditableAccountPhoto[] => {
    return photos.map((photo) => ({
      id: photo.id,
      url: photo.url,
      markedForDeletion: false,
    }))
  }

  let tempIdCounter = -1
  const createNewPhoto = (file: File): EditableAccountPhoto => {
    return {
      id: tempIdCounter--,
      url: URL.createObjectURL(file),
      file,
    }
  }

  const analyzePhotosChanges = (photos: EditableAccountPhoto[]): AccountPhotosChanges => {
    const toDelete: number[] = []
    const toUpload: File[] = []

    for (const photo of photos) {
      if (photo.file) {
        toUpload.push(photo.file)
      } else if (photo.markedForDeletion) {
        toDelete.push(photo.id)
      }
    }
    const hasChanges = toDelete.length > 0 || toUpload.length > 0
    return { toDelete, toUpload, hasChanges }
  }

  // Getters
  const hasChanges = computed(() => {
    if (!originalProfile.value) return false
    const profileChanged = (Object.keys(originalProfile.value) as Array<keyof AccountSchema>).some(
      (key) => profile.value[key] !== originalProfile.value![key],
    )
    const photosChanges = analyzePhotosChanges(photos.value)
    return profileChanged || photosChanges.hasChanges
  })

  const photosChanges = computed(() => analyzePhotosChanges(photos.value))

  // Actions
  async function initialize(account: AccountOut) {
    profile.value = normalizeAccountProfile(account)
    photos.value = parsePhotos(account.photos)
    originalProfile.value = { ...profile.value }
    currentAccountId.value = account.id
  }

  function addPhoto(file: File) {
    const newPhoto = createNewPhoto(file)
    photos.value = [newPhoto, ...photos.value]
  }

  function togglePhotoDelete(index: number) {
    const photo = photos.value[index]
    if (!photo) return

    if (photo.file) {
      // Новое фото - удаляем из массива
      photos.value.splice(index, 1)
    } else {
      // Существующее фото - помечаем для удаления
      photo.markedForDeletion = !photo.markedForDeletion
    }
  }

  function createPayload(uploadedPaths: string[]): AccountUpdatePayload {
    const { toDelete } = photosChanges.value
    return {
      ...profile.value,
      photos: {
        upload: uploadedPaths,
        delete: toDelete,
      },
    }
  }

  function reset() {
    if (isSaving.value) return
    profile.value = {} as AccountSchema
    photos.value = []
    originalProfile.value = null
    currentAccountId.value = null
  }

  return {
    // State
    profile,
    photos,
    currentAccountId,
    isSaving,

    // Getters
    hasChanges,
    photosChanges,

    // Actions
    initialize,
    addPhoto,
    togglePhotoDelete,
    createPayload,
    reset,
  }
})
