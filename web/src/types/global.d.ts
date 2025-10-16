interface TelegramUser {
  id: number
  first_name: string
  last_name?: string
  username?: string
  photo_url?: string
  auth_date: number
  hash: string
}

interface LogEntry {
  status: 'info' | 'error' | 'success' | 'warning'
  message: string
  payload?: object
}

interface UploadTask {
  file: File
  status: 'pending' | 'uploading' | 'fulfilled' | 'rejected'
  s3path?: string
  error?: string
  promise?: Promise<string>
}

interface UploadAllResult {
  fulfilled: string[]
  rejected: File[]
}

type JobStatus = 'pending' | 'running' | 'finished' | 'failed'

interface BackgroundJob {
  id: string
  name: string
  status: JobStatus
  createdAt: Date
  logs: LogEntry[]
  onComplete?: (job: BackgroundJob) => void
}
