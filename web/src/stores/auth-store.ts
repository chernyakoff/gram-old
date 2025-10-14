import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { useApi } from '@/composables/use-api'
import type { UserLoginIn, UserLoginOut, UserOut } from '@/types/openapi'

export const useAuthStore = defineStore('auth', () => {
  const user = ref<UserOut | null>(null)
  const accessToken = ref<string | null>(localStorage.getItem('accessToken'))
  const isAuthenticated = computed(() => !!accessToken.value)
  const { api } = useApi()
  async function login(user: UserLoginIn) {
    const data = await api<UserLoginOut>('auth', {
      method: 'POST',
      body: user,
    })
    accessToken.value = data.accessToken
    localStorage.setItem('accessToken', data.accessToken)
    await fetchUser()
  }

  async function logout() {
    user.value = null
    accessToken.value = null
    localStorage.removeItem('accessToken')
    try {
      await api('auth/logout', { method: 'POST' })
    } catch {
      // ignore errors
    }
  }

  async function refreshTokens() {
    try {
      const data = await api<UserLoginOut>('auth/refresh', {
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

  async function fetchUser() {
    const me = await api<UserOut>('auth/me')
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
