import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { useApi } from '@/composables/useApi'

export const useAuthStore = defineStore('auth', () => {
  // --- state ---
  const user = ref<User | null>(null)
  const accessToken = ref<string | null>(localStorage.getItem('accessToken'))

  // --- getters ---
  const isAuthenticated = computed(() => !!accessToken.value)

  const { api } = useApi()

  // --- actions ---
  async function login (telegramUser: TelegramUser) {
    // тело запроса теперь через body, а не data
    const data = await api<{ accessToken: string }>('auth', {
      method: 'POST',
      body: telegramUser,
    })

    accessToken.value = data.accessToken
    localStorage.setItem('accessToken', data.accessToken)
    await fetchUser()
  }

  async function logout () {
    user.value = null
    accessToken.value = null
    localStorage.removeItem('accessToken')
    try {
      await api('auth/logout', { method: 'POST' })
    } catch {
      // ignore errors
    }
  }

  async function refreshTokens () {
    try {
      const data = await api<{ accessToken: string }>('auth/refresh', {
        method: 'POST',
      })
      accessToken.value = data.accessToken
      localStorage.setItem('accessToken', data.accessToken)
      return true
    } catch {
      logout()
      return false
    }
  }

  async function fetchUser () {
    const me = await api<User>('auth/me')
    user.value = me
  }

  return {
    user,
    accessToken,
    isAuthenticated,
    login,
    logout,
    refreshTokens,
    fetchUser,
  }
})
