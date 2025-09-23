interface User {
  id: number
  hasLicense: boolean
  role: 'ADMIN' | 'USER'
  username?: string
  firstName?: string
  lastName?: string
  photoUrl?: string
}

interface Workflow {
  id: string
}

interface Proxy {
  id: number
  host: string
  port: number
  username: string
  password: string
  country: string
  createdAt: Date
}

interface AccountPhoto {
  id: number
  url: string
}

interface Account {
  id: number
  phone: string
  country: string
  createdAt: Date
  active: boolean
  busy: boolean
  premium: boolean
  twofa: string | null
  username: string | null
  firstName: string | null
  lastName: string | null
  about: string | null
  channel: string | null
  photos: AccountPhoto[]
}

interface EditableAccountPhoto extends AccountPhoto {
  file?: File
  markedForDeletion?: boolean
}

interface TelegramUser {
  id: number
  firstName: string
  lastName?: string
  username?: string
  photoUrl?: string
  authDate: number
  hash: string
}
interface LogEntry {
  status: 'info' | 'error' | 'success' | 'warning'
  message: string
  payload?: object
}

interface PresignedResponse {
  s3path: string
  url: string
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
/*
export interface UploadTask {
  file: File
  status: 'pending' | 'uploading' | 'fulfilled' | 'rejected'
  s3path?: string
  error?: string
  promise?: Promise<string>
}

export interface UploadAllResult {
  fulfilled: string[]
  rejected: File[]
}

*/
type JobStatus = 'pending' | 'running' | 'finished' | 'failed'

interface BackgroundJob {
  id: string
  name: string
  status: JobStatus
  createdAt: Date
  logs: LogEntry[]
  onComplete?: (job: BackgroundJob) => void
}
