import { ref } from 'vue'
import ky, { type Options } from 'ky'
import { useAuthStore } from '@/stores/auth-store'
import { keysToCamel, keysToSnake } from '@/utils/case'

// Преобразуем ошибки в строку
export function getErrorValue(e: unknown): string {
  if (e instanceof Error) return e.message
  return 'Неизвестная ошибка'
}

// ---------- Ky instance с Authorization + snake/camel + refresh ----------
function createKy(prefixUrl: string) {
  const authStore = useAuthStore()

  const instance = ky.create({
    prefixUrl,
    credentials: 'include',
    timeout: 5 * 60 * 1000,
    hooks: {
      beforeRequest: [
        async (request) => {
          if (authStore.accessToken) {
            request.headers.set('Authorization', `Bearer ${authStore.accessToken}`)
          }
        },
      ],
      afterResponse: [
        async (request, options, response) => {
          if (response.status === 401) {
            // Never try to refresh on refresh/logout calls, otherwise we can end up in a retry loop.
            if (request.url.includes('/auth/refresh') || request.url.includes('/auth/logout')) {
              return response
            }

            const headers =
              options.headers instanceof Headers ? options.headers : new Headers(options.headers)

            if (!headers.get('_retry')) {
              headers.set('_retry', 'true')

              const success = await authStore.refreshTokens()
              if (success) {
                headers.set('Authorization', `Bearer ${authStore.accessToken}`)
                // Используем instance вместо глобального ky
                return instance(request, { ...options, headers })
              }
            }
          }

          return response
        },
      ],
    },
  })

  return instance
}
/* function normalizeEndpoint(endpoint: string): string {
  return endpoint.replace(/\/?(?=\?|$)/, '/')
} */

type AnyOptions = Omit<Options, 'body'> & { body?: unknown }

function getEnvValue(key: 'API_URL' | 'USERS_URL'): string | undefined {
  const runtimeEnv = (window as unknown as { env?: Record<string, string> }).env
  return import.meta.env[key] || runtimeEnv?.[key]
}

// ---------- useApiCall composable с ky ----------
export function useApi() {
  const loading = ref(false)
  const error = ref<string | null>(null)
  const success = ref(false)
  const apiUrl = getEnvValue('API_URL') || 'http://localhost:8833'
  const usersUrl = getEnvValue('USERS_URL') || 'http://localhost:8834'
  const kyInstance = createKy(apiUrl)
  const kyUsersInstance = createKy(usersUrl)

  const requestJson = async <T>(
    instance: ReturnType<typeof ky.create>,
    endpoint: string,
    options?: AnyOptions,
  ): Promise<T> => {
    loading.value = true
    error.value = null
    success.value = false

    try {
      const opts = { ...options }

      if (opts.body && !(opts.body instanceof FormData)) {
        opts.body = JSON.stringify(keysToSnake(opts.body))
        opts.headers = { ...opts.headers, 'Content-Type': 'application/json' }
      }

      const response = await instance(endpoint, opts as Options)
      const data = await response.json()

      success.value = true
      return keysToCamel(data) as T
    } catch (e) {
      error.value = getErrorValue(e)
      throw e
    } finally {
      loading.value = false
    }
  }

  const requestBlob = async (
    instance: ReturnType<typeof ky.create>,
    endpoint: string,
    options?: AnyOptions,
  ): Promise<Blob> => {
    loading.value = true
    error.value = null
    success.value = false

    try {
      const opts = { ...options }

      if (opts.body && !(opts.body instanceof FormData)) {
        opts.body = JSON.stringify(keysToSnake(opts.body))
        opts.headers = { ...opts.headers, 'Content-Type': 'application/json' }
      }

      const response = await instance(endpoint, opts as Options)
      const blob = await response.blob()

      success.value = true
      return blob
    } catch (e) {
      error.value = getErrorValue(e)
      throw e
    } finally {
      loading.value = false
    }
  }

  const api = async <T>(endpoint: string, options?: AnyOptions): Promise<T> =>
    requestJson<T>(kyInstance, endpoint, options)

  const apiUsers = async <T>(endpoint: string, options?: AnyOptions): Promise<T> =>
    requestJson<T>(kyUsersInstance, endpoint, options)

  const apiBlob = async (endpoint: string, options?: AnyOptions): Promise<Blob> =>
    requestBlob(kyInstance, endpoint, options)

  const apiUsersBlob = async (endpoint: string, options?: AnyOptions): Promise<Blob> =>
    requestBlob(kyUsersInstance, endpoint, options)

  return { api, apiUsers, apiBlob, apiUsersBlob, loading, error, success }
}
