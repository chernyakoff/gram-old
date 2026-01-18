import { defineStore } from 'pinia'
import { reactive } from 'vue'
import { useApi } from '@/composables/use-api'
import type { PresignedIn, PresignedOut } from '@/types/openapi'

export type UploadedFileMeta = {
  storagePath: string
  filename: string
  contentType: string
  fileSize: number
}

export type UploadTask<T> = {
  file: File
  status: 'pending' | 'uploading' | 'fulfilled' | 'rejected'
  error?: string
  result?: T
  promise?: Promise<T>
}

export type UploadAllResult<T> = {
  fulfilled: T[]
  rejected: File[]
}

export const useUploadStore = defineStore('upload', () => {
  const tasks = reactive<UploadTask<UploadedFileMeta>[]>([])
  const { api } = useApi()

  async function uploadOne(file: File, path: string): Promise<UploadedFileMeta> {
    const task: UploadTask<UploadedFileMeta> = { file, status: 'pending' }
    tasks.push(task)

    const promise = (async () => {
      try {
        task.status = 'uploading'

        const body: PresignedIn = { path, filename: file.name }

        const { s3path, url } = await api<PresignedOut>('s3/presigned', {
          method: 'POST',
          body,
        })

        const res = await fetch(url, { method: 'PUT', body: file })
        if (!res.ok) throw new Error(`S3 upload failed: ${res.status}`)

        const result: UploadedFileMeta = {
          storagePath: s3path,
          filename: file.name,
          contentType: file.type,
          fileSize: file.size,
        }

        task.status = 'fulfilled'
        task.result = result
        return result
      } catch (err: unknown) {
        task.status = 'rejected'
        task.error = err instanceof Error ? err.message : 'Unknown error'
        throw err
      }
    })()

    task.promise = promise
    return promise
  }

  function uploadAll(files: File[], path: string) {
    tasks.splice(0, tasks.length)
    return files.map((file) => uploadOne(file, path))
  }

  async function waitForAll(): Promise<UploadAllResult<UploadedFileMeta>> {
    const results = await Promise.allSettled(tasks.map((t) => t.promise!))

    return {
      fulfilled: results
        .filter((r): r is PromiseFulfilledResult<UploadedFileMeta> => r.status === 'fulfilled')
        .map((r) => r.value),

      rejected: results
        .filter((r): r is PromiseRejectedResult => r.status === 'rejected')
        .map((_, i) => tasks[i]?.file)
        .filter(Boolean) as File[],
    }
  }

  return { tasks, uploadOne, uploadAll, waitForAll }
})
