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
function createKy() {
  const authStore = useAuthStore()

  const instance = ky.create({
    prefixUrl: import.meta.env.API_URL,
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

// ---------- useApiCall composable с ky ----------
export function useApi() {
  const loading = ref(false)
  const error = ref<string | null>(null)
  const success = ref(false)
  const kyInstance = createKy()

  const api = async <T>(endpoint: string, options?: AnyOptions): Promise<T> => {
    loading.value = true
    error.value = null
    success.value = false

    try {
      const opts = { ...options }

      if (opts.body && !(opts.body instanceof FormData)) {
        opts.body = JSON.stringify(keysToSnake(opts.body))
        opts.headers = { ...opts.headers, 'Content-Type': 'application/json' }
      }

      const response = await kyInstance(endpoint, opts as Options)
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

  return { api, loading, error, success }
}
