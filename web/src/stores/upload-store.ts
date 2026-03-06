import { defineStore } from 'pinia'
import { reactive } from 'vue'
import { useApi } from '@/composables/use-api'
import type { PresignedIn, PresignedOut } from '@/types/openapi'

export const useUploadStore = defineStore('upload', () => {
  const tasks = reactive<UploadTask[]>([])
  const { api } = useApi()

  async function uploadOne(file: File, path: string) {
    const task: UploadTask = { file, status: 'pending' }
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

        task.status = 'fulfilled'
        task.s3path = s3path
        return s3path
      } catch (err: unknown) {
        task.status = 'rejected'
        task.error = err instanceof Error ? err.message : 'Unknown error'
        throw err
      }
    })()

    task.promise = promise
    return promise
  }

  // Запускает все загрузки параллельно и возвращает массив промисов
  function uploadAll(files: File[], path: string) {
    tasks.splice(0, tasks.length)
    return files.map((file) => uploadOne(file, path))
  }

  // Ждём завершения всех задач
  async function waitForAll(): Promise<UploadAllResult> {
    const results = await Promise.allSettled(tasks.map((t) => t.promise!))

    return {
      fulfilled: results
        .filter((r): r is PromiseFulfilledResult<string> => r.status === 'fulfilled')
        .map((r) => r.value),
      rejected: results
        .filter((r): r is PromiseRejectedResult => r.status === 'rejected')
        .map((r, i) => tasks[i]?.file)
        .filter(Boolean) as File[],
    }
  }

  return { tasks, uploadOne, uploadAll, waitForAll }
})
