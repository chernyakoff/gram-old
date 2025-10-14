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

  return ky.create({
    prefixUrl: import.meta.env.API_URL,
    credentials: 'include',
    hooks: {
      beforeRequest: [
        async (request) => {
          if (authStore.accessToken)
            request.headers.set('Authorization', `Bearer ${authStore.accessToken}`)
        },
      ],
      afterResponse: [
        async (request, options, response) => {
          if (response.status === 401) {
            options.headers = options.headers || new Headers()
            const headers =
              options.headers instanceof Headers ? options.headers : new Headers(options.headers)
            if (!headers.get('_retry')) {
              headers.set('_retry', 'true')

              const authStore = useAuthStore()
              const success = await authStore.refreshTokens()
              if (success) {
                headers.set('Authorization', `Bearer ${authStore.accessToken}`)
                options.headers = headers
                return ky(request.url, options)
              }
            }
          }

          // Конвертация JSON → camelCase
          if (response.ok && response.headers.get('content-type')?.includes('application/json')) {
            const data = await response.json()
            return new Response(JSON.stringify(keysToCamel(data)), response)
          }

          return response
        },
      ],
    },
  })
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
    //endpoint = normalizeEndpoint(endpoint)
    try {
      const opts = { ...options }

      if (opts.body && !(opts.body instanceof FormData) && typeof opts.body !== 'string') {
        opts.body = JSON.stringify(keysToSnake(opts.body))
        opts.headers = { ...opts.headers, 'Content-Type': 'application/json' }
      }

      const response = await kyInstance(endpoint, opts as Options)
      const data = await response.json()
      success.value = true
      return data as T
    } catch (e: unknown) {
      error.value = getErrorValue(e)
      throw e
    } finally {
      loading.value = false
    }
  }

  return { api, loading, error, success }
}
